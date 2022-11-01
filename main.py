import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    uvicorn.run("app:app", host='0.0.0.0', port=port)
