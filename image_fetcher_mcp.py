"""Image Fetcher MCP Server."""

import asyncio
import base64
import io
import mimetypes
import uvicorn
from typing import List, Union

from PIL import Image
import mcp.server.fastmcp as fm
from mcp.types import TextContent, ImageContent

MAX_IMAGE_SIZE = (512, 512)
JPEG_QUALITY = 40

mcp = fm.FastMCP("Image Fetcher")


@mcp.tool()
async def get_image_from_url(url: str) -> List[Union[ImageContent, TextContent]]:
  """
  Fetches an image from a URL and returns the image content as base64 along with metadata.
  The returned ImageContent contains the full image for visual analysis.
  """
  try:
    url = url.strip()

    process = await asyncio.create_subprocess_exec(
        "curl",
        "-sL",
        "-H", "Accept: image/*,*/*;q=0.8",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
      return [
          TextContent(
              type="text",
              text=f"Failed to fetch image. Curl error: {stderr.decode()}"
          )
      ]

    try:
      img = Image.open(io.BytesIO(stdout))
      img.thumbnail(MAX_IMAGE_SIZE, Image.LANCZOS)
      output = io.BytesIO()
      if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        img.save(output, format="PNG", optimize=True)
        mime_type = "image/png"
      else:
        img = img.convert("RGB")
        img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        mime_type = "image/jpeg"
      encoded_image = base64.b64encode(output.getvalue()).decode("utf-8")
    except Exception:
      encoded_image = base64.b64encode(stdout).decode("utf-8")
      mime_type, _ = mimetypes.guess_type(url)
      if mime_type is None:
        mime_type = "application/octet-stream"

    return [
        ImageContent(type="image", data=encoded_image, mimeType=mime_type),
    ]

  except Exception as e:
    return [TextContent(type="text", text=str(e))]


def main() -> None:
  """The main entry point for the server."""
  uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
  main()