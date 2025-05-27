We believe in writing clean code based on modern frameworks.

Guiding principles: Maintainability, understandability, and ease of debugging are very important. KISS. Fewer lines of code is almost always better. Avoid lots of boilerplate. Avoid NIH syndrome. It’s ok to take some shortcuts as long as it results in an easy to understand solution (but highlight any known deficiencies in comments). Avoid catching exceptions if doing so will mask detailed error context and traceback.

Dependencies: In general I want to use the latest stable version of all dependencies. Pegging versions is fine, but don’t generate code that already and version pegged if you can avoid it. A way to fetch the latest and then let that would be better. Make sure you are using documentation and best practices in your code that are for the newest and most current version.

Language/framework: Use whatever language makes the most sense, but prefer python and then plain JavaScript if possible. Flask is the preferred framework for simple web apps. I want to manage python dependencies using `uv`. I don't like `pandas`.

Hosting/deployment: I like serverless (Cloudflare Worker, Google Cloud Functions/Cloud Run). Self hosted is fine too especially if it can run on arm64.
