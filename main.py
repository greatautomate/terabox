import logging
import json
import requests
import re
import html
import os
import tempfile
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, BadRequest, RPCError
from pyrogram.enums import ParseMode
import aiohttp
import aiofiles

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InstagramDownloaderBot:
    def __init__(self):
        self.api_id = int(os.getenv('API_ID'))
        self.api_hash = os.getenv('API_HASH')
        self.bot_token = os.getenv('BOT_TOKEN')

        self.terabox_api_url = "http://smex.unaux.com/fastbox.php"

        self.app = Client(
            "instagram_bot",
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.bot_token,
            workdir="./sessions",
            sleep_threshold=60,
            max_concurrent_transmissions=1
        )

        os.makedirs("./sessions", exist_ok=True)
        os.makedirs("./downloads", exist_ok=True)

        self.setup_handlers()

    def setup_handlers(self):
        """Set up command and message handlers"""

        @self.app.on_message(filters.command("start"))
        async def start_handler(client, message: Message):
            await self.start_command(message)

        @self.app.on_message(filters.command("help"))
        async def help_handler(client, message: Message):
            await self.help_command(message)

        @self.app.on_message(filters.text & ~filters.command(["start", "help"]))
        async def message_handler(client, message: Message):
            await self.handle_message(message)

    async def start_command(self, message: Message):
        """Send welcome message with HTML formatting"""
        welcome_text = """🎬📸 <b>Multi-Platform Downloader Bot</b>

Welcome! Send me any supported URL and I'll download it for you.

<b>What I can download:</b>
🎥 <b>Instagram Reels</b> - Video content (up to 2GB)
📸 <b>Instagram Photos</b> - Single or multiple images
📱 <b>Instagram Posts</b> - Any Instagram post content
📦 <b>TeraBox Files</b> - Videos and files from TeraBox

<b>How to use:</b>
1. Copy a supported link
2. Send it to me  
3. Wait for processing ⏳
4. Get your content! 📥

<b>Supported platforms:</b>
• Instagram (Reels/Photos)
• TeraBox (Files/Videos)

Type /help for more information.

<b>Developer:</b> @medusaXD

<b>Enhanced Features:</b>
✅ Large file support (up to 2GB)
✅ Fast async downloads
✅ Progress tracking
✅ Error recovery
✅ Multi-platform support
✅ JavaScript challenge bypass"""

        try:
            await message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending start message: {e}")
            await message.reply_text("Bot started successfully!")

    async def help_command(self, message: Message):
        """Send help information with HTML formatting"""
        help_text = """📖 <b>Help - Multi-Platform Downloader Bot</b>

<b>Commands:</b>
• <code>/start</code> - Start the bot
• <code>/help</code> - Show this help message

<b>Supported Content:</b>
🎥 <b>Instagram Reels</b> - Downloaded as MP4 (up to 2GB)
📸 <b>Instagram Photos</b> - Downloaded as JPG (HD Quality)
📦 <b>TeraBox Files</b> - Any file type supported by TeraBox

<b>Features:</b>
🚀 <b>Fast Downloads</b> - Async processing
📊 <b>Progress Tracking</b> - Real-time updates
🔄 <b>Auto Retry</b> - Handles temporary failures
💾 <b>Large Files</b> - Supports files up to 2GB
🛡️ <b>Error Handling</b> - Comprehensive error recovery
🌐 <b>Multi-Platform</b> - Instagram + TeraBox support
🤖 <b>Anti-Bot Bypass</b> - JavaScript challenge solving

<b>Developer:</b> @medusaXD"""

        try:
            await message.reply_text(help_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending help message: {e}")

    def extract_all_urls(self, text: str):
        """Extract all supported URLs from message text"""
        instagram_urls = re.findall(r'https?://(?:www\.)?instagram\.com/(?:reel|p)/[a-zA-Z0-9_-]+/?', text)

        terabox_patterns = [
            r'https?://(?:www\.)?terabox\.com/s/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?terabox\.com/sharing/link\?surl=[a-zA-Z0-9_-]+',
            r'https?://(?:www\.)?1024tera\.com/s/[a-zA-Z0-9_-]+/?'
        ]

        terabox_urls = []
        for pattern in terabox_patterns:
            matches = re.findall(pattern, text)
            terabox_urls.extend(matches)

        return {
            'instagram': instagram_urls,
            'terabox': terabox_urls
        }

    async def solve_js_challenge_with_playwright(self, url: str):
        """Solve JavaScript challenge using Playwright"""
        try:
            from playwright.async_api import async_playwright

            target_url = f"{self.terabox_api_url}?url={url}"
            logger.info(f"Solving JS challenge for: {target_url}")

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-features=TranslateUI',
                        '--disable-extensions'
                    ]
                )

                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )

                page = await context.new_page()
                await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)

                try:
                    await page.wait_for_function(
                        "() => document.body.innerText.includes('{') || window.location.href.includes('&i=1')",
                        timeout=15000
                    )
                except:
                    logger.warning("Timeout waiting for JS challenge")

                content = await page.content()
                final_url = page.url
                await browser.close()

                logger.info(f"Final URL: {final_url}")

                if '{' in content and '"status"' in content:
                    json_match = re.search(r'\{[^<>]*"status"[^<>]*\}', content)
                    if json_match:
                        try:
                            json_data = json.loads(json_match.group())
                            logger.info("Successfully extracted JSON from page content")
                            return json_data
                        except json.JSONDecodeError:
                            pass

                return None

        except ImportError:
            logger.error("Playwright not installed")
            return None
        except Exception as e:
            logger.error(f"Error solving JS challenge: {str(e)}")
            return None

    async def get_terabox_data(self, url: str):
        """Get TeraBox file data with Playwright"""
        logger.info(f"Attempting to fetch TeraBox data for URL: {url}")

        try:
            data = await self.solve_js_challenge_with_playwright(url)
            if data and data.get('status') == 'success':
                logger.info("TeraBox data extraction successful!")
                return self.process_terabox_response(data)
        except Exception as e:
            logger.error(f"Error in TeraBox data extraction: {e}")

        return None

    def process_terabox_response(self, data):
        """Process the TeraBox API response"""
        try:
            if data.get('status') == 'success' and 'data' in data and len(data['data']) > 0:
                file_info = data['data'][0]

                return {
                    "status": "success",
                    "type": "terabox",
                    "file_name": file_info.get('name', 'terabox_file'),
                    "direct_link": file_info.get('fast_stream_url', ''),
                    "thumb": file_info.get('thumbnail', ''),
                    "size": file_info.get('size_formatted', 'Unknown'),
                    "sizebytes": 0,
                    "dev": "@medusaXD"
                }
            else:
                logger.error(f"TeraBox API unsuccessful response: {data}")
                return None

        except Exception as e:
            logger.error(f"Error processing TeraBox response: {str(e)}")
            return None

    async def get_reel_data(self, url: str):
        """Get Instagram reel data"""
        target_url = "https://snapdownloader.com/tools/instagram-reels-downloader/download"

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {'url': url}
                async with session.get(target_url, params=params, headers=headers) as response:
                    if response.status != 200:
                        return None

                    html_content = await response.text()

            video_match = re.search(r'<a[^>]+href="([^"]+\.mp4[^"]*)"[^>]*>', html_content)
            video_url = video_match.group(1) if video_match else ""

            if video_url:
                video_url = html.unescape(video_url)
                return {
                    "status": "success",
                    "type": "video",
                    "video": video_url,
                    "thumbnail": "",
                    "dev": "@medusaXD"
                }

            return None

        except Exception as e:
            logger.error(f"Error getting reel data: {str(e)}")
            return None

    async def get_photo_data(self, url: str):
        """Get Instagram photo data"""
        target_url = "https://snapdownloader.com/tools/instagram-photo-downloader/download"

        try:
            headers = {
                'authority': 'snapdownloader.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'referer': 'https://snapdownloader.com/tools/instagram-photo-downloader',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {'url': url}
                async with session.get(target_url, params=params, headers=headers) as response:
                    if response.status != 200:
                        return None

                    html_content = await response.text()

            soup = BeautifulSoup(html_content, 'html.parser')

            resolutions = ['1080 x 1080', '750 x 750', '640 x 640']
            links = []

            for res in resolutions:
                download_links = soup.find_all('a', class_=lambda x: x and 'btn-download' in x)
                for a in download_links:
                    text = a.get_text(strip=True)
                    href = a.get('href', '')
                    if href:
                        href = html.unescape(href)
                        if f"Download ({res})" in text or res.replace(' x ', 'x') in href:
                            links.append(href)
                if links:
                    break

            if links:
                return {
                    "status": "success",
                    "type": "photos", 
                    "total_image": len(links),
                    "images": [{"image": link} for link in links],
                    "dev": "@medusaXD"
                }
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting photo data: {str(e)}")
            return None

    def detect_url_type(self, url: str):
        """Detect the type of URL"""
        if 'instagram.com' in url:
            if '/reel/' in url:
                return 'instagram_reel'
            elif '/p/' in url:
                return 'instagram_mixed'
        elif 'terabox.com' in url or '1024tera.com' in url:
            return 'terabox'
        return 'unknown'

    async def download_file_async(self, url: str, filename: str, progress_message: Message = None):
        """Download file asynchronously with progress tracking"""
        try:
            timeout = aiohttp.ClientTimeout(total=600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Download failed with status: {response.status}")
                        return False

                    file_size = int(response.headers.get('content-length', 0))
                    logger.info(f"Downloading file of size: {file_size/1024/1024:.1f}MB")

                    async with aiofiles.open(filename, 'wb') as file:
                        downloaded = 0
                        last_update = 0

                        async for chunk in response.content.iter_chunked(8192):
                            await file.write(chunk)
                            downloaded += len(chunk)

                            if file_size > 0 and progress_message:
                                progress = (downloaded / file_size) * 100
                                if progress - last_update >= 10:
                                    try:
                                        await progress_message.edit_text(
                                            f"⏬ <b>Downloading...</b> {progress:.1f}%",
                                            parse_mode=ParseMode.HTML
                                        )
                                        last_update = progress
                                    except Exception as e:
                                        logger.warning(f"Progress update failed: {e}")

                    logger.info(f"Download completed: {downloaded/1024/1024:.1f}MB")
                    return True

        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

    async def handle_message(self, message: Message):
        """Handle incoming messages with enhanced error handling"""
        try:
            message_text = message.text
            urls = self.extract_all_urls(message_text)

            all_urls = urls['instagram'] + urls['terabox']

            if not all_urls:
                await message.reply_text(
                    "❌ <b>No supported URL found!</b>\n\nSend a valid Instagram or TeraBox URL.",
                    parse_mode=ParseMode.HTML
                )
                return

            if urls['terabox']:
                url = urls['terabox'][0]
                await self.process_terabox_url(url, message)
            elif urls['instagram']:
                url = urls['instagram'][0]
                url_type = self.detect_url_type(url)
                await self.process_instagram_url(url, url_type, message)

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            try:
                await message.reply_text("❌ <b>An error occurred. Please try again.</b>", parse_mode=ParseMode.HTML)
            except:
                await message.reply_text("An error occurred. Please try again.")

    async def process_terabox_url(self, url: str, message: Message):
        """Process TeraBox URLs"""
        processing_msg = None
        try:
            processing_msg = await message.reply_text(
                "🔄 <b>Processing TeraBox URL...</b>\n<i>Solving JavaScript challenge...</i>", 
                parse_mode=ParseMode.HTML
            )

            data = await self.get_terabox_data(url)

            if data and data.get('status') == 'success':
                await self.process_terabox_file(data, message, processing_msg, url)
            else:
                await processing_msg.edit_text(
                    "❌ <b>Failed to fetch TeraBox content</b>\n\nThe file might be private or the URL is invalid.",
                    parse_mode=ParseMode.HTML
                )

        except Exception as e:
            logger.error(f"Error processing TeraBox URL: {e}")
            if processing_msg:
                try:
                    await processing_msg.edit_text("❌ <b>Processing failed</b>", parse_mode=ParseMode.HTML)
                except:
                    pass

    async def process_terabox_file(self, data: dict, original_message: Message, processing_msg: Message, original_url: str):
        """Process and send TeraBox files with enhanced stability"""
        temp_filename = None
        try:
            direct_link = data.get('direct_link', '')
            file_name = data.get('file_name', 'terabox_file')
            size_text = data.get('size', 'Unknown')

            if not direct_link:
                await processing_msg.edit_text("❌ <b>No download link found</b>", parse_mode=ParseMode.HTML)
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = os.path.splitext(file_name)[1] if '.' in file_name else '.mp4'
            temp_filename = f"./downloads/terabox_{timestamp}{file_extension}"

            await processing_msg.edit_text(
                f"⏬ <b>Downloading TeraBox file...</b>\n📁 <b>File:</b> {file_name}\n📊 <b>Size:</b> {size_text}", 
                parse_mode=ParseMode.HTML
            )

            logger.info(f"Starting download from: {direct_link}")
            success = await self.download_file_async(direct_link, temp_filename, processing_msg)

            if not success:
                await processing_msg.edit_text("❌ <b>Failed to download file</b>", parse_mode=ParseMode.HTML)
                return

            actual_file_size = os.path.getsize(temp_filename)
            logger.info(f"Downloaded file size: {actual_file_size/1024/1024:.1f}MB")

            if actual_file_size > 2 * 1024 * 1024 * 1024:
                await processing_msg.edit_text(
                    f"❌ <b>File too large!</b>\n\nSize: {actual_file_size/1024/1024:.1f}MB",
                    parse_mode=ParseMode.HTML
                )
                return

            await processing_msg.edit_text("📤 <b>Uploading file...</b>", parse_mode=ParseMode.HTML)

            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
            is_video = any(file_extension.lower().endswith(ext) for ext in video_extensions)

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if is_video:
                        await original_message.reply_video(
                            temp_filename,
                            caption=f"🔗 Original URL: {original_url}",
                            file_name=file_name
                        )
                    else:
                        await original_message.reply_document(
                            temp_filename,
                            caption=f"🔗 Original URL: {original_url}",
                            file_name=file_name
                        )

                    logger.info("File sent successfully!")
                    break

                except RPCError as e:
                    logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    else:
                        await processing_msg.edit_text("❌ <b>Upload failed after multiple attempts</b>", parse_mode=ParseMode.HTML)
                        return
                except FloodWait as e:
                    logger.info(f"FloodWait: sleeping for {e.value} seconds")
                    await asyncio.sleep(e.value)
                    continue

            try:
                await processing_msg.delete()
            except:
                pass

        except Exception as e:
            logger.error(f"Error processing TeraBox file: {str(e)}")
            if processing_msg:
                try:
                    await processing_msg.edit_text("❌ <b>Processing failed</b>", parse_mode=ParseMode.HTML)
                except:
                    pass
        finally:
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                    logger.info("Temp file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

    async def process_instagram_url(self, url: str, url_type: str, message: Message):
        """Process Instagram URLs"""
        processing_msg = await message.reply_text("🔄 <b>Processing Instagram URL...</b>", parse_mode=ParseMode.HTML)

        if url_type in ['instagram_reel', 'instagram_mixed']:
            data = await self.get_reel_data(url)

            if data and data.get('status') == 'success':
                await self.process_video(data, message, processing_msg, url)
                return

            if url_type == 'instagram_mixed':
                data = await self.get_photo_data(url)
                if data and data.get('status') == 'success':
                    await self.process_photos(data, message, processing_msg)
                    return

        await processing_msg.edit_text(
            "❌ <b>Failed to fetch Instagram content</b>",
            parse_mode=ParseMode.HTML
        )

    async def process_video(self, data: dict, original_message: Message, processing_msg: Message, original_url: str):
        """Process and send Instagram video content"""
        temp_filename = None
        try:
            video_url = data.get('video', '')
            if not video_url:
                await processing_msg.edit_text("❌ <b>No video URL found</b>", parse_mode=ParseMode.HTML)
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"./downloads/reel_{timestamp}.mp4"

            await processing_msg.edit_text("⏬ <b>Downloading video...</b>", parse_mode=ParseMode.HTML)

            success = await self.download_file_async(video_url, temp_filename, processing_msg)

            if not success:
                await processing_msg.edit_text("❌ <b>Failed to download video</b>", parse_mode=ParseMode.HTML)
                return

            await processing_msg.edit_text("📤 <b>Uploading video...</b>", parse_mode=ParseMode.HTML)

            file_size = os.path.getsize(temp_filename)
            if file_size > 2 * 1024 * 1024 * 1024:
                await processing_msg.edit_text(
                    f"❌ <b>File too large!</b>\n\n<b>File size:</b> {file_size/1024/1024:.1f}MB\n<b>Maximum allowed:</b> 2GB",
                    parse_mode=ParseMode.HTML
                )
                return

            try:
                await original_message.reply_video(
                    temp_filename,
                    caption=f"🔗 Original URL: {original_url}"
                )
                await processing_msg.delete()
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await original_message.reply_video(
                    temp_filename,
                    caption=f"🔗 Original URL: {original_url}"
                )
                await processing_msg.delete()
            except Exception as e:
                logger.error(f"Error sending video: {str(e)}")
                await processing_msg.edit_text("❌ <b>Failed to send video</b>", parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            if processing_msg:
                try:
                    await processing_msg.edit_text("❌ <b>Failed to process video</b>", parse_mode=ParseMode.HTML)
                except:
                    pass
        finally:
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                    logger.info("Temp video file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp video file: {e}")

    async def process_photos(self, data: dict, original_message: Message, processing_msg: Message):
        """Process and send Instagram photo content"""
        try:
            images = data.get('images', [])
            if not images:
                await processing_msg.edit_text("❌ <b>No images found</b>", parse_mode=ParseMode.HTML)
                return

            total_images = len(images)
            await processing_msg.edit_text(f"📸 <b>Downloading {total_images} image(s)...</b>", parse_mode=ParseMode.HTML)

            for idx, img_data in enumerate(images, 1):
                img_url = img_data.get('image', '')
                if not img_url:
                    continue

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_filename = f"./downloads/photo_{timestamp}_{idx}.jpg"

                await processing_msg.edit_text(
                    f"⏬ <b>Downloading image {idx}/{total_images}...</b>",
                    parse_mode=ParseMode.HTML
                )

                success = await self.download_file_async(img_url, temp_filename)

                if success:
                    try:
                        await original_message.reply_photo(
                            temp_filename,
                            caption=f"📸 <b>Image {idx}/{total_images}</b>\n\n<b>Downloaded by Multi-Platform Bot</b>\n<b>Developer:</b> @medusaXD",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"Error sending photo {idx}: {e}")

                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

                await asyncio.sleep(1)

            await processing_msg.delete()

        except Exception as e:
            logger.error(f"Error processing photos: {str(e)}")
            if processing_msg:
                try:
                    await processing_msg.edit_text("❌ <b>Failed to process images</b>", parse_mode=ParseMode.HTML)
                except:
                    pass

    def run(self):
        """Start the bot with enhanced error handling"""
        try:
            logger.info("🚀 Starting Multi-Platform Downloader Bot...")
            self.app.run()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")

bot = InstagramDownloaderBot()

if __name__ == "__main__":
    bot.run()
