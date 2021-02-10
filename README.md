# Sanal Kiwo[^1]

*A realistic Telegram chatbot in the making*

[Try it out!](https://t.me/sanalkiwobot)

---

![(Türkçe kılavuz için tıklayınız.)](./README_TR.md)

The bot's main feature is that besides the commands starting with "/", it also tries to understand a command call from the regular messages. Every text message is passed to a dispatcher function named "read_incoming". If any keywords are found, the appropriate action is taken.

Using this method, the bot can reply to some chatting prompts or call one of its commands.

### Commands:

* **/start** (or **/baslat**) starts the bot and sends an introductory message.
* **/help** (or **/yardim**) sends a message explaining the bot's functionalities.
* **/corona** presents one or more countries' daily COVID-19 data, retrieved from [this repository](https://github.com/CSSEGISandData/COVID-19).
* **/subscription** (or **/abonelik**) toggles a chat's subscription to automatic announcements from the admins.
* **/abort** (or **/iptal**) aborts any ongoing "dialogue" between the bot and the user that involve more than one messages. That is, if the chat is in a special state, the state is cleared. (At the moment, no multiple-message dialogues exist for non-admin users.)

#### Administrator commands:

* **/db_backup** sends a backup of `resources/chat_data/` directory to the admin(s).
* **/announce** (or **/duyur**) initiates a dialogue between the calling admin and the bot. Following the dialogue, the admin can send an announcement message to the bot's every subscribed user. The sender is asked to confirm the message before sending.
* **/revokeannc** (or **/duyurusil**) tries to delete the last announcement's message from every user. This command can be used as a last resort in case of an accident.

## REQUIREMENTS

Python 3.6 or greater is required.

Required modules:

* emoji *([This](https://github.com/carpedm20/emoji/tree/d73e3063e30bbce8cdbab873a57e4fdef1bf7c12) version used and listed in `requirements.txt`, later versions are untested.)*
* pandas (1.0.3)
* python-telegram-bot (12.8)
* requests (2.21.0)

## SETUP

**1)** Install the required modules. You may use `pip`/`pip3`:

```
pip install -r requirements.txt
```

**2)** [Create an account](https://core.telegram.org/bots#3-how-do-i-create-a-bot) for the bot and obtain the bot's token.

**3)** If you will deploy the bot using a hosting site (e.g Heroku, Glitch...), set up environment variables named `DEPLOYED` and `TOKEN` on the hosting service. Set `DEPLOYED` to `True` and `TOKEN` to the bot's token.

If you plan to run the bot locally, you do not need to set up an environment variable. To set up the token, rewrite `resources/.token.txt` such that it only contains your bot's token.

**4)** If you want to designate any private or group chats as administrators, you need to obtain their IDs first. Currently, the bot does not have a function for this, but various methods exist:

* Using [@get_id_bot](https://telegram.me/get_id_bot).

* Visiting `https://api.telegram.org/botXXXXXX/getUpdates` where `XXXXXX` is the token of your bot, sending a message from the desired chat, and hitting refresh. You should see the ID under `result -> 0 -> message -> chat -> id`.

* Inserting temporary code in `read_incoming` function that prints out `update.message.chat.id`, running the bot (see step 5), and sending a message from the desiring chat.

Once you obtain the IDs, enter them in `resources/chat_data/admin_chats.txt`, one for each line.
Empty lines and lines starting with `#%#` will be skipped. The examples below are valid:

```
1111111
-2222222
3333333
```

```
#%# Admins group:
-1111111

#%# User 1:
2222222
```

**5)** Deploy the bot, or start running it locally:

```
$ python sanalkiwobot.py
```

If you wish to host on Heroku, you can use the included Procfile containing this command.

## NOTES

Special types of comments can be found throughout `sanalkiwobot.py`:

* `FIXME` comments indicate a broken functionality that needs to be fixed ASAP.
* `TODO` comments indicate planned improvements as well as new features.
* `IDEA` comments indicate proposed features that are not essential for the bot's functioning.
* `NOTE` comments hold fairly important information to be considered during development.

The program is written in English; however, the bot operates using Turkish. A full English translation and a language selection feature is under development.

## LICENSE

This program is licensed under the MIT License. For more information, see the file `LICENSE`.

---

[^1]: The bot somewhat imitates my texting style. Its name means "Virtual Kiwo" which is derived from my name (Kıvanç).
