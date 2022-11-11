# GST:LIVE Backend Server

## Running the Server

Backend server requires a PostgreSQL Database and the following environment variables:

- DATABASE_URL: PostgreSQL database url.
- FRONTEND_HOMEPAGE: URL to the frontend homepage.
- OSU_CLIENT_ID: osu! client ID - can be taken from https://osu.ppy.sh/home/account/edit.
- OSU_CLIENT_SECRET: osu! client secret - can be taken from https://osu.ppy.sh/home/account/edit.
- DISCORD_CLIENT_ID: Discord client ID - can be taken from https://discord.com/developers/applications.
- DISCORD_CLIENT_SECRET: Discord client secret - can be taken from https://discord.com/developers/applications.
- REDIRECT_URI: Main URL for the backend server.
- SECRET: Secret string for hashing the user ids.
- PORT: Port for server to run on.

### Docker

Build and run the Dockerfile with:

```bash
export PORT=8000
docker build -t gstlive-backend .
docker run -d -p $PORT:$PORT --env-file .env gstlive-backend
```

### Python

Create a virtual environment & install the requirements.

```bash
python -m venv gst-env
source gst-env/bin/activate
pip install -r requirements.txt
```

Run the server using:

```bash
python main.py
```
