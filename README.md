<div align="center">
  <h1>SciAstra bot to prevent sharing prohibited links</h1>
</div>

<p align="center">
  This bot helps to distinguish link and delete them fro chats. It also helps in keeping track of the number of doubts asked by the students etc. 
</p>


# Quick start
- Create a file that ends with `_allowed_urls.txt` and any URL in that file will be allowed to share in the channel/group.
- Create `config.py` with TOKEN="YOUR_TOKEN" in it
- Now install all the required dependencies using `pip install -r requirements.txt`
- Run the bot using `python main.py` or `python3 main.py` depending on the version.

# Author

- [@Aman](https://www.github.com/AmanRathoreP)
   - [GitHub](https://www.github.com/AmanRathoreP)
   - [Telegram](https://t.me/aman0864)
   - Email -> *aman.proj.rel@gmail.com*

# Technicalities
- `config.py` stores sensitive information don't share it with anyone
- Note that sub-urls of the allowed URLs will also be allowed for example if `example.in` is allowed then `example.in/anything` and `example.in/anything/anything` will also be allowed
