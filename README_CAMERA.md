# Camera Configuration Setup

The tracking daemon and video feed require camera credentials to access the RTSP stream.

## Setup Instructions

1. **Copy the example config:**
   ```bash
   cd ~/Documents/_PROGETTI/z21-Terminal
   cp config.local.json.example config.local.json
   ```

2. **Edit with your credentials:**
   ```bash
   micro config.local.json  # or nano, vim, etc.
   ```

3. **Add your camera credentials:**
   ```json
   {
     "camera": {
       "username": "your_tapo_username",
       "password": "your_tapo_password"
     }
   }
   ```

4. **Done!** The config is gitignored and won't be committed.

## How It Works

Camera configuration is split between two files:

- **`config.json`** (tracked in git): IP, port, stream name, resolution
- **`config.local.json`** (gitignored): Username and password only

The system automatically merges `config.local.json` over `config.json` at runtime.

## Troubleshooting

If you see this error:
```
❌ ERROR: Camera credentials missing
   Add credentials to config.local.json (gitignored):
   { "camera": { "username": "...", "password": "..." } }
```

Just run the setup steps above.

## Stream Options

- **stream1** - 1080P (high quality, slower)
- **stream2** - 720P (recommended for real-time tracking)
- **stream3** - 480P (low quality, fastest)

We use **stream2** (720P) for best balance between quality and performance.

Stream selection is configured in `config.json` under `camera.stream`.
