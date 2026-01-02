# Camera Configuration Setup

The tracking daemon and video feed require camera credentials to access the RTSP stream.

## Setup Instructions

1. **Copy the example config:**
   ```bash
   cd ~/Documents/_PROGETTI/z21-Terminal
   cp camera_config.json.example camera_config.json
   ```

2. **Edit with your credentials:**
   ```bash
   micro camera_config.json  # or nano, vim, etc.
   ```

3. **Set your camera credentials:**
   ```json
   {
     "camera_ip": "192.168.1.4",
     "camera_port": 554,
     "stream": "stream2",
     "username": "your_tapo_username",
     "password": "your_tapo_password"
   }
   ```

4. **Done!** The config is gitignored and won't be committed.

## Troubleshooting

If you see this error:
```
❌ ERROR: Camera config not found at camera_config.json
   Create it from template: cp camera_config.json.example camera_config.json
```

Just run the setup steps above.

## Stream Options

- **stream1** - 1080P (high quality, slower)
- **stream2** - 720P (recommended for real-time tracking)
- **stream3** - 480P (low quality, fastest)

We use **stream2** (720P) for best balance between quality and performance.
