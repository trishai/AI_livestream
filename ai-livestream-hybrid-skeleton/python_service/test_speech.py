import asyncio
import edge_tts

async def main():
    text = "Xin chào, đây là AI livestream test tiếng Việt"

    communicate = edge_tts.Communicate(
        text=text,
        voice="vi-VN-HoaiMyNeural"   # giọng nữ
    )

    await communicate.save("output.mp3")

if __name__ == "__main__":
    asyncio.run(main())