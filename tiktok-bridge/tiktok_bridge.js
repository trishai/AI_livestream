import { TikTokLiveConnection, WebcastEvent } from 'tiktok-live-connector';

const USERNAME = "bot.obaxua";
const N8N_WEBHOOK = "http://localhost:5678/webhook/ai-livestream-comment-test";

const connection = new TikTokLiveConnection(USERNAME, {
  processInitialData: true
});

// connect
connection.connect()
  .then(state => {
    console.log("✅ Connected to room:", state.roomId);
  })
  .catch(err => {
    console.error("❌ Connect fail:", err);
  });

// auto reconnect
connection.on("disconnected", () => {
  console.log("⚠️ Disconnected → reconnecting...");
  setTimeout(() => connection.connect(), 3000);
});

// listen comment
connection.on(WebcastEvent.CHAT, async (data) => {
  const comment = data.comment;
  const user = data.user.uniqueId;

  console.log(`💬 ${user}: ${comment}`);

  if (!comment || comment.length < 2) return;

  try {
    await fetch(N8N_WEBHOOK, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        comment: comment,
        source_user: user
      })
    });
  } catch (err) {
    console.error("❌ Webhook error:", err.message);
  }
});