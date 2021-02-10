#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A bot with miscellaneous commands and simple chatting features.
For a more detailed explanation, please see the readme file of the project.

The bot runs until it receives a termination signal on the command line.
"""

import datetime as dt
import logging
import os
import shutil
import string
from functools import wraps
from random import randint
from uuid import uuid4

import emoji
import pandas as pd
import requests
from telegram import Bot, ChatAction, TelegramError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext import messagequeue as mq
from telegram.utils.request import Request


class SanalkiwoBot(Bot):
    """Bot subclass for decorating some of its methods.
    
    MessageQueue is used to decorate the send_message method, in order to avoid
    flood limits.
    """
    
    def __init__(self, *args, queue_msgs=True, msg_queue=None, **kwargs):
        super(SanalkiwoBot, self).__init__(*args, **kwargs)
        
        # Attributes for the MessageQueue decorator:
        self._is_messages_queued_default = queue_msgs
        self._msg_queue = msg_queue or mq.MessageQueue()
    
    def stop(self):
        try:
            self._msg_queue.stop()
        except:
            logger.warning(
                "MessageQueue.stop() failed while stopping SanalkiwoBot!"
            )
    
    # Note that the wrapped versions below can now accept the decorator's
    #   'queued' and 'isgroup' optional arg.s. 'queued' defaults to True and
    #   'isgroup' defaults to False.
    
    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        return super(SanalkiwoBot, self).send_message(*args, **kwargs)
    
    # If necessary, also wrap other send_* methods here.
    # NOTE: Wrapping send_document breaks db_backup. (FIXME?)


class UpdaterBotStop(Updater):
    """Updater subclass which also calls the bot's stop method when terminated.
    
    Intented to be used with SanalkiwoBot class, which is a subset of
    telegram.Bot with a stop method.
    """
    
    def signal_handler(self, signum, frame):
        super().signal_handler(signum, frame)
        self.bot.stop()


## Non-command (helper) functions: ##

def choose_one(ls):
    """Randomly choose one element of the input iterable."""
    
    # TODO: Refactor this function so that it cycles on the list witch each call
    #   instead. Make it so that it "pops" the last element, appends it to
    #   "head" of list, returns the head... or similar...
    #   Rename the func. accordingly.
    if type(ls) != list:
        ls = list(ls)
    
    return ls[randint(0, len(ls) - 1)]


def get_first_key(dictn, val):
    """Find first occurence of a key for a given value in a dictionary."""
    
    for i in dictn:
        if dictn[i] == val:
            return i
    
    logger.error(f"getfirstkey: Value {str(val)} doesn't exist in dictionary.")
    return ""


def get_phrases(ls):
    """Get the set of phrases made by combining the strings in the given list.
    
    A phrase is obtained by concatenating any number of words in given order and
    without skipping any of them.
    Thus, if the given list has n words, the number of "phrases" possible is
    (n(n+1))/2.
    """
    r = set()
    len_ls = len(ls)
    
    for i in range(len_ls):
        phrase = ""
        for j in range(i, len_ls):
            if j != i: phrase += " "
            phrase += ls[j]
            
            r.add(phrase)
    
    return r
    

def get_preposition(inp, apos=True):
    """Return the given string with the Turkish preposition "de/da" appended.
    
    Do not add an apostrophe if the optional arg. apos is False.
    """
    
    # Some exceptional cases:
    if inp == "abd":
        return "abd'de" if apos else "abdde"
    elif inp.endswith("ları") or inp.endswith("lari"):
        return inp + "'nda" if apos else inp + "nda"
    elif inp.endswith("leri"):
        return inp + "'nde" if apos else inp + "nde"
    
    harden = False
    suffix = ""
    if apos: suffix += "'"
    
    for j in inp[::-1]:
        if j in ["f", "s", "t", "k", "ç", "ş", "h", "p"]:
            harden = True
        elif j in ["a", "ı", "o", "u"]:
            suffix += ("ta" if harden else "da")
            
            return inp + suffix
        elif j in ["e", "i", "ö", "ü"]:
            suffix += ("te" if harden else "de")
            
            return inp + suffix

    # No vowels in word:
    return inp + "'da" if apos else inp + "da"


def lower_tr(s):
    """Call str.lower, but convert 'I' to 'ı' instead of 'i'.
    
    This is done to adhere to the Turkish alphabet.
    """
    
    r = ""
    for i in s:
        if i == "I":
            r += "ı"
        else:
            r += i.lower()
    
    return r


def datetime_format(date, caller=None):
    """Convert given datetime.datetime object to a string of appropriate form.
    
    Choose the format according to the "caller" arg., which is a string
    indicating the name of the function calling this function.
    """
    
    if caller == "corona":
        return date.strftime("%m-%d-%Y")
    
    if caller == "db_backup":
        return date.strftime("%Y-%m-%d-%H-%M-%S")
    
    # Default case, used for displaying the date in message:
    return date.strftime("%d.%m.%Y")


def send_action(act):
    """Wrapper for sending an action to the user while handling a request."""
    
    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=act
            )
            
            return func(update, context, *args, **kwargs)
        
        return command_func
    
    return decorator


# Chat database maintenance func.s: #

def db_add(src_path, db, new_entry):
    """Adds a string entry to a database file and the given set variable.
    
    If it already exists in the set, do not take any action.
    """
    
    if new_entry not in db:
        with open(src_path, "r+") as f:
            f.seek(0, 2)
            f.write(str(new_entry) + "\n")
            f.seek(0)
        
        db.add(new_entry)


def db_remove(src_path, db, chat_id):
    """Removes a string entry from a database file and the given set variable.
    
    If it does not already exist in the set, do not take any action.
    """
    
    if chat_id in db:
        with open(src_path, "r+") as f:
            l = f.readlines()
            f.seek(0)
            for i in l:
                if i != (str(chat_id) + "\n"):
                    f.write(i)
            f.truncate()
        
        db.remove(chat_id)


def db_cleanup(context):
    """Clean up temporary files which are not expected to be needed again."""
    
    now = dt.datetime.now()
    
    logger.info("Executing db_cleanup.")
    
    # Cache directory cleanup: #
    
    for f in os.scandir(PATH_CACHE_DIR):
        fname = f.name
        
        if not fname.startswith("readme"):
            logger.info("Removing from " + PATH_CACHE_DIR + f": {fname}")
            os.remove(f)
    
    # /corona files: #
    # Cleans up COVID data older than 2 days.
    
    for f in os.scandir(PATH_COVID_DIR):
        fname = f.name
        
        # f.name[:-4] strips the file extension:
        if (fname.endswith(".csv") and
            (now - dt.datetime.strptime(fname[:-4], "%m-%d-%Y")).days > 2):
            logger.info("Removing from " + PATH_COVID_DIR + f": {fname}")
            os.remove(f)
        
    # (Repeat with us_data/ dir:)
    for f in os.scandir(PATH_COVID_DIR + "us_data/"):
        fname = f.name
        if (fname.endswith(".csv") and
            (now - dt.datetime.strptime(fname[:-4], "%m-%d-%Y")).days > 2):
            logger.info(
                "Removing from " + PATH_COVID_DIR + f"us_data/: {fname}"
            )
            os.remove(f)
    
    logger.info("Exiting db_cleanup.")


def db_read(src_path, read_type=set, read_int=False):
    """Read string data from a file into a variable of given type.
    
    Read from the file at 'src_path', line by line, skipping certain lines and
    removing trailing whitespace.
    
    If 'read_int' is True, convert the resulting string to int.
    Return read data as an object of the desired type specified by 'read_type'.
    """
    
    def skip(s):
        """Bool func. for skipping a line. "#%# " is chosen as a comment
        indicator. """
        
        return s == "\n" or s.startswith("#%# ")
    
    if read_type is list:
        result = list()
        with open(src_path, "r") as f:
            for i in f.readlines():
                if not skip(i):
                    result.append(int(i.strip()) if read_int else i.strip())
    elif read_type is set:
        result = set()
        with open(src_path, "r") as f:
            for i in f.readlines():
                if not skip(i):
                    result.add(int(i.strip()) if read_int else i.strip())
    elif read_type is dict:
        # Process the lines in pairs: First the key, then the corresponding
        #   value, and then the next key... and so on.
        result = dict()
        with open(src_path, "r") as f:
            key_temp = ""
            
            for i in f.readlines():
                if not skip(i):
                    if key_temp:
                        result[key_temp] = (
                            int(i.strip()) if read_int else i.strip()
                        )
                        key_temp = ""
                    else:
                        key_temp = (int(i.strip()) if read_int else i.strip())
    elif read_type is str:
        # Only read the first line of the file, strip and return it:
        with open(src_path, "r") as f:
            result = f.readline().rstrip()
    else:
        logger.error("db_read: read_type is not list, str, set or dict.")
        return None
    
    return result


# For now, this backup function is manually called in the code after every
#   database update. If the user base grows and the backups get too
#   overwhelming, the manual calls can be removed and the func. can be called
#   automatically in a specific time interval instead.
@send_action(ChatAction.UPLOAD_DOCUMENT)
def db_backup(update, context, called_with_message=True):
    """Send a temporary db. backup zip file to the administrators.
    
    The administrator chat IDs are listed under the DB_ADMIN_CHATS global.
    
    If the bot calls this function by itself, send the message only to the
    administrator group chats. In this case, called_with_message
    flag must be set to False.
    
    If an administrator calls this function through the /db_backup command in an
    administrator chat, the file is sent only to that chat.
    """
    
    # TODO: Do not run if DB_ADMIN_CHATS is empty
    
    if called_with_message and (update.effective_chat.id not in DB_ADMIN_CHATS):
        update.message.reply_text("yalnızca admin chatlerde!")
        return
    
    zipname = "chat_data_" + ("DEPLOYED_" if DEPLOYED else "LOCAL_") \
        + datetime_format(dt.datetime.now(), "db_backup") + "_" \
        + uuid4().hex[:8]
    
    logger.info("Beginning .zip creation in db_backup.")
    zippath = shutil.make_archive(
        PATH_CACHE_DIR + zipname, "zip", PATH_CHAT_DATA_DIR, logger=logger
    )
    
    with open(zippath, "rb") as z:
        chat = update.effective_chat.id
        
        if called_with_message and (chat in DB_ADMIN_CHATS):
            context.bot.send_document(chat, z, filename=zipname + ".zip")
        else:
            for i in DB_ADMIN_CHATS:
            # NOTE: The conditional below relies on the negative chat ID
            #   property of groups. Keep in mind that this property is not
            #   officially defined and may be subject to change.
                if i < 0:
                    context.bot.send_document(i, z, filename=zipname + ".zip")
    
    os.remove(zippath)
    logger.info("Removed the temporary .zip. Exiting db_backup.")


# Custom message sending functions: #

def notify_admins(context, message, groups_only=True):
    """Notifies administrator chats by sending a message.
    
    The administrator chat IDs are listed under the DB_ADMIN_CHATS global.
    
    If the groups_only arg. is True, the message is sent only to admin. groups.
    """
    
    # NOTE: This function relies on the negative chat ID property of groups.
    #   Keep in mind that this property is not officially defined and may be
    #   subject to change.
    
    if groups_only:
        for i in DB_ADMIN_CHATS:
            if i < 0:
                context.bot.send_message(i, message, isgroup=True)
    else:
        for i in DB_ADMIN_CHATS:
            context.bot.send_message(i, message, isgroup=(i < 0))


def greet(update, context):
    """Respond to a greeting message."""
    
    sender = update.message.from_user
    uname = sender.username
    # Keep in mind that uname is None if the account does not have an username.
    # On the other hand, the first name is guaranteed to exist for all users.
    
    # Some easter eggs for specific people can be included below:
    if uname == "kivanct":
        update.message.reply_text("selam reel kiwo")
    else:  # Default behavior
        # IDEA: add some random "friendly" words?
        update.message.reply_text(f"selam {lower_tr(sender.first_name)}")


## Command handlers: ##
# These take the two arguments update and context. (On-command functions - can
#   be called via "/command" after setting handler in main func.)

def start(update, context):
    """Send an introduction message and update the set of known chats."""
    
    chat_id = update.effective_chat.id
    
    if chat_id not in db_chats:
        # Add chat ID to database (and thus to the announcement list):
        db_add(PATH_CHATS, db_chats, chat_id)
        # Manual backup of the updated chat data. Change if becomes too
        #   overwhelming:
        db_backup(update, context, called_with_message=False)
    
    # TODO: Include link to source
    update.message.reply_markdown_v2(MSG_START)


# TODO: Detect this in reply from "kiwo yardım" etc. (i.e. add nlp text version)
def help_info(update, context):
    """Send a message explaining the bot's abilities and properties."""
    # TODO: Also inform the admins about the admin func.s
    # TODO: Mention COVID data source
    update.message.reply_markdown_v2(MSG_HELP)


# FIXME: does ri_set convert İ to i? I should be converted both to i and to ı.
# TODO: When asked, tell the user his/her ID
# TODO: When asked, tell the user the chat's ID
def read_incoming(update, context):
    """Dispatch the incoming message to the appropriate functionality.
    
    If the chat is in a specific state (as indicated in dict_chat_states),
    "dispatch" the message and behave accordingly.
    
    Else,
    Check for keywords in the user message and either reply with a special
    response or execute the corresponding command if appropriate keyword
    combinations are detected.
    """
    
    # When new commands are introduced, do not forget to test the bot's behavior
    #   when they are executed in the same message.
    
    global dict_last_anncs
    global dict_annc_temp
    
    # Incoming message object:
    inc = update.message
    
    # List of detected distinct emojis in message text:
    emojis = emoji.distinct_emoji_lis(inc.text)
    
    # Reduced and splitted versions of incoming message:
    #   "Reduced" means lowercase with removed emoji and punctuations.
    #   The set also includes potential phrases to check, formed by conscutive
    #   and non-skipped combinations of words. For example: 
    #   If inc is "A, b C", ri_set is {"a", "a b", "a b c", "b", "b c", "c"}.
    
    # Lower and remove punctuations:
    red_inc = lower_tr(
        inc.text.translate(str.maketrans('', '', string.punctuation))
    )
    # Remove emojis:
    for i in emojis:
        red_inc = red_inc.replace(i, "")
    
    ri_list = red_inc.split()
    
    len_ri_list = len(ri_list)
    word_limit = len_ri_list if len_ri_list < 50 else 50
    
    # ri_set is used for keyword recognition in incoming messages.
    # (If the message is too long, it may be inefficient to work with n(n+1)/2
    #   elements. Thus, only the first 50 words of a message are read.)
    ri_set = get_phrases(ri_list[:word_limit])
    
    # Add one of each used emoji type to ri_set:
    for i in emojis:
        ri_set.add(i)
    
    chat_is_private = (inc.chat.type == "private")
    chat_id = inc.chat.id
    replied_to = inc.reply_to_message
    reply_with = inc.reply_text
    
    is_reply_to_bot = (
        (replied_to is not None)
        and replied_to.from_user.id == BOT_ID
    )
    targeted_to_bot = (
        chat_is_private
        or is_reply_to_bot
        or (ri_set & (WS_KIWO | WS_GROUP))
    )
    
    ## Dispatching block: ##
    
    state = ""
    
    try:
        state = dict_chat_states[chat_id]
        
        logger.info(f"Detected chat state: {state}")
    except KeyError:
        logger.debug("No detected state for the chat.")
    
    if state:
        if state == "announce_lv1":
            # Get the announcement message to be sent
            
            logger.debug("Enter announce_lv1")
            
            # If sender in not an admin, warn and wait for admin message
            if inc.from_user.id not in DB_ADMIN_CHATS:
                logger.debug("Non-admin: Exit announce_lv1")
                reply_with("yalnız adminler duyuru yollayabilir!")
            else:
                dict_annc_temp[chat_id] = inc.text
                
                inc.reply_markdown_v2(
                    "şu mesajı duyuru olarak *bütün bilinen kullanıcılara*"
                    ' yolluyorum\. lütfen onaylamak için "evet", vazgeçmek için'
                    ' "hayır" yazın:'
                )
                
                context.bot.send_message(
                    chat_id,
                    dict_annc_temp[chat_id],
                    isgroup=(not chat_is_private)
                )
                dict_chat_states[chat_id] = "announce_lv2"
        elif state == "announce_lv2":
            # Confirm the announcement message to be sent.
            #   If confirmed, send it to every non-blacklisted user.
            
            logger.debug("Enter announce_lv2")
            # IDEA: Use custom inline keyboard for confirmation
            
            # If sender is not an admin, warn and wait for admin message
            if inc.from_user.id not in DB_ADMIN_CHATS:
                logger.debug("Non-admin: Exit announce_lv1")
                reply_with("yalnız adminler duyuru yollayabilir!")
            else:
                if red_inc in {"evet", "yes"}:
                    logger.info(
                        "Beginning mass announcement: Sending to every"
                        " non-blacklisted chat in the database."
                    )
                    
                    reply_with(
                        "tamamdır, duyuruları göndermeye başlıyorum. bir"
                        " aksilik söz konusu olursa dediğim gibi /duyurusil ile"
                        " duyuruları geri çekmeyi deneyebilirsiniz."
                    )
                    
                    notify_admins(
                        context,
                        "yeni bir duyuru kullanıcılara gönderilmeye"
                        " başlandı..."
                    )
                    
                    dict_last_anncs = dict()
                    
                    recipients = db_chats - db_annc_blist
                    
                    # The message is guaranteed to exist in the buffer:
                    annc = dict_annc_temp[chat_id]
                    
                    # Send to every recipient, log and fill dict_last_anncs in
                    #   the process
                    
                    for i in recipients:
                        # NOTE: The isgroup argument below relies on the
                        #   negative chat ID property of groups. Keep in
                        #   mind that this property is not officially
                        #   defined and may be subject to change.
                        sent = context.bot.send_message(
                            i,
                            annc,
                            isgroup=(i < 0)
                        )
                        
                        # sent is a telegram.utils.promise.Promise object
                        
                        dict_last_anncs[i] = sent.result().message_id
                        
                        logger.info(
                            f"Announcement sent to recipient ID {i} with"
                            f" message ID {dict_last_anncs[i]}"
                        )
                    
                    del dict_annc_temp[chat_id]
                    del dict_chat_states[chat_id]
                    
                    logger.info("Finished mass announcement.")
                elif red_inc in {"hayır", "no"}:
                    reply_with(
                        "peki, yeni duyuru mesajı için bekliyorum. duyuru"
                        " yollamaktan vazgeçerseniz /iptal komutunu kullanın."
                    )
                    
                    dict_chat_states[chat_id] = "announce_lv1"
                else:
                    reply_with('lütfen "evet" veya "hayır" ile cevaplayın.')
        else:
            # Should never execute - ensure all possible states are checked
            reply_with(
                "benimle yürüttüğün bir işlem var ama ne olduğunu tam"
                " çıkaramıyorum. olası bir aksiliği engellemek için"
                " /iptal komutunu çalıştırıyor ve işlemi iptal ediyorum."
                " kusura bakma, en kısa zamanda sıkıntıyı çözücem... şimdi"
                " hiçbir şey olmamış gibi yazışmaya devam edebiliriz."
            )
            
            del dict_chat_states[chat_id]
            
            logger.warning(
                f"read_incoming called with unknown state: {state} - State is"
                " cancelled."
            )
            
            notify_admins(
                context,
                f"bilinmeyen state ({state}) ile bir mesaj alındı. state iptal"
                " edildi."
            )
        
        return
    
    ## Message-specific replies: ##
    # Observe how the order and separation of the if-elif blocks create
    #   precedence and independence in detections. Thus, multiple replies can be
    #   made to a single message, in a known order.
    
    if targeted_to_bot:
        # Replies for when the bot but NOT any other group member is targeted: #
        if ri_set.isdisjoint(WS_GROUP):
            # Currently unused
            pass
        # Replies for when the bot OR any other group member is targeted: #
        # Responding to a personal or general group greeting:
        if ri_set & WS_GREET:
            greet(update, context)
        
        # Responding to a personal or general group "what's up?":
        if ri_set & WS_WHATSUP:
            reply_with(choose_one(LIST_WHATSUP_REPLY))
        
        # Detecting command requests: #
        if chat_is_private or (ri_set & WS_REQUEST):
            # /corona:
            # FIXME: "papua yeni gine" triggers for both "gine" and "papua yeni
            #   gine".
            if ri_set & WS_CORONA:
                locations = set()
                key_set = set(DICT_LOCATIONS.keys())
                val_set = set(DICT_LOCATIONS.values())
                
                # Stripped input message for leftover detection
                exclude = (WS_CORONA
                        | WS_REQUEST
                        | WS_KIWO
                        | WS_GREET
                        | WS_WHATSUP)
                
                for phrase in ri_set:
                    compare = {phrase}
                    if phrase.endswith("da") or phrase.endswith("de") \
                            or phrase.endswith("ın") or phrase.endswith("in"):
                        compare.add(phrase[:-2])
                    if phrase.endswith("nde") or phrase.endswith("nde") \
                            or phrase.endswith("nın") \
                            or phrase.endswith("nin"):
                        compare.add(phrase[:-3])
                    
                    for i in compare:
                        # Do not break when found, compare set may hold multiple
                        #   keys
                        if i in key_set:
                            # Check for a translated location name in message
                            if DICT_LOCATIONS[i] not in locations:
                                locations.add(DICT_LOCATIONS[i])
                            exclude |= get_phrases(phrase.split())
                        elif i in val_set:
                            # Check for the original location name in message
                            if i not in locations:
                                locations.add(i)
                            exclude |= get_phrases(phrase.split())
                
                # Excluding phrases that contain excluded words. The previous
                #   loop must be completed first.
                for phrase in ri_set:
                    for i in phrase.split():
                        if i in exclude and phrase not in exclude:
                            exclude.add(phrase)
                            break
                
                if ri_set - exclude:  # Inform user about unknown words
                    reply_with(
                        "mesajda ülke ismi olarak tanıyamadığım kelimeler var."
                        " doğru yazılmış bir ülke ismini tanıyamadıysam lütfen"
                        " o kelimedeki ekleri çıkarıp tekrar dene."
                    )
                elif not locations:
                    # No location names detected, default to "Turkey"
                    locations.add("Turkey")
                
                if locations:
                    logger.info(
                        f"Got locations: {locations}, calling func. now."
                    )
                    reply_with("hemen bakıyorum...")
                    
                    for i in locations:
                        corona(update, context, i)
    else:  # Not targeted_to_bot
        # Detecting and responding to a group greeting with keywords:
        if red_inc in ["selamlar", "merhabalar"]:
            greet(update, context)
        
        # Detecting and responding to a group "what's up?" with keyword:
        if ri_set & {"nabersiniz"}:
            reply_with(choose_one(LIST_WHATSUP_REPLY))


# TODO: Also inform about the day's new stats
# TODO: Should also support the world's total data
@send_action(ChatAction.TYPING)
def corona(update, context, location="Turkey"):
    """Get the latest COVID-19 data of the requested location & present it.
    
    The location arg. must be a value of the dictionary DICT_LOCATIONS.
    """
    
    reply_with = update.message.reply_text
    
    if location not in DICT_LOCATIONS.values():
        logger.error("corona func. called with an invalid location name!")
        
        notify_admins(context, "corona fonk. da csv okunamadı!")
        
        reply_with(
            "özür diliyorum, bir şeyleri çok fena batırdım. daha sonra tekrar"
            " dener misin?"
        )
        
        return
    
    global last_covid_get_date
    
    msg_date = update.message.date
    chat_id = update.effective_chat.id
    chat_is_group = update.effective_chat.type != "private"
    
    date = datetime_format(msg_date, "corona")
    url_tries = 0
    
    if context.args:
        # If there are multiple arg.s, only the first one is used.
        # TODO: Should handle multiple arguments. Recursion implementation is
        #   probably not worth it. Pass the arg.s to read_incoming?
        
        try:
            location = DICT_LOCATIONS[lower_tr(context.args[0])]
        except KeyError:
            loc_candidate = context.args[0].capitalize()
            if loc_candidate in DICT_LOCATIONS.values():
                location = loc_candidate
            else:
                reply_with(
                    'ülke adını (henüz) bilmiyorum. "-da", "-de" gibi bir ek ya'
                    ' da özel karakterler mi kullandın? lütfen ekleri çıkarıp'
                    ' tekrar dene.'
                )
                
                return
    
    while url_tries < 5:
        req_file_name = date + ".csv"
        
        if location == "US":
            url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19" \
                + "/master/csse_covid_19_data/csse_covid_19_daily_reports_us/" \
                + req_file_name
            
            req_file_path = PATH_COVID_DIR + "us_data/" + req_file_name
        else:
            # TODO: Is a separate URL for US really needed?
            url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19" \
                + "/master/csse_covid_19_data/csse_covid_19_daily_reports/" \
                + req_file_name
            
            req_file_path = PATH_COVID_DIR + req_file_name
        
        # If requested file exists in database and enough time has passed since
        #   last retrieval (In this case, 10800 seconds (3 hours)):
        #   (Comparing seconds since datetime subtraction returns timedelta
        #   object which only has days, sec.s and microsec.s stored internally)
        
        if (os.path.exists(req_file_path) and
            (dt.datetime.now() - last_covid_get_date).seconds < 10800):
            logger.info(
                "Requested file has already been retrieved into the"
                " database in the last 3 hours."
            )
            break
        else:  # If requested file doesn't exist or enough time has passed
            data_response = requests.get(url)
            
            if int(data_response.status_code) // 100 == 2:  # 2xx HTTP status
                # Note that requests module handles 3xx (redirection) and issues
                #   the new status code instead.
                logger.info(f"Retrieved file from: {url}")
                
                with open(req_file_path, "wb") as f:
                    f.write(data_response.content)
                    logger.info("File written in database.")
                
                last_covid_get_date = dt.datetime.now()
                
                break
            else:
                # Making date var. one day earlier (getting prev. day of the
                #   datetime.datetime object):
                logger.info(
                    f"Non-2xx HTTP response for {date} - trying to get the"
                    " previous day's data."
                )
                
                date = datetime_format(msg_date - dt.timedelta(1), "corona")
                url_tries += 1
    else:
        reply_with(
            "aradığım kaynağı ya 5 gündür güncellemiyorlar ya da komple"
            " uçurdular. umarım salgın sona erdiği içindir ve bağlantımda bi"
            " sorun yoktur."
        )
        return
    
    try:
        df = pd.read_csv(req_file_path)
    except pd.errors.ParserError:
        logger.error("Couldn't parse COVID database csv!")
        
        notify_admins(context, "corona fonk. da csv okunamadı!")
        
        reply_with(
            "acayip bir şeyler oldu, nedense elimdeki veritabanını"
            " okuyamıyorum. bilgiyi aldığım kaynakta ya da direkt bende bir"
            " yamukluk olabilir."
        )
        
        return
    
    logger.info("Got COVID database.")
    
    # TODO: Handle country or data type reading from .csv error as well.
    
    case = 0
    active = 0
    recoveries = 0
    deaths = 0
    
    location_data = df.loc[df["Country_Region"] == location]
    
    # Iterate for every location name match in the CSV. This enables the
    #   summation of data released seperately for different states/provinces
    #   (e.g US, Australia...).
    for i in location_data.itertuples(index=False):
        t_conf = i.Confirmed
        t_actv = i.Active
        t_recv = i.Recovered
        t_dths = i.Deaths
        
        if pd.notnull(t_conf): case += t_conf
        if pd.notnull(t_actv) and t_actv > 0: active += int(t_actv)
        if pd.notnull(t_recv): recoveries += int(t_recv)
        if pd.notnull(t_dths): deaths += t_dths
        
    logger.info(
        f"Got case: {case}, active: {active}, recoveries: {recoveries},"
        f" deaths: {deaths}"
    )
    
    if location == "United Kingdom":
        location_text = "birleşik krallık'ta"
    else:
        location_text = get_preposition(get_first_key(DICT_LOCATIONS, location))
    
    covidtext = datetime_format(msg_date - dt.timedelta(url_tries)) \
        + f" itibariyle {location_text} toplam {case:,} resmi vaka olmuş." \
        f"\nverilere göre bunlardan {active:,} tanesi aktif." \
        f"\ngeri kalan kişilerin {deaths:,} tanesi hayatını kaybetmiş," \
        f" {recoveries:,} tanesi iyileşmiş.\n"
    
    if not recoveries:
        covidtext += "0 iyileşen kötüymüş be. ülkenin henüz tüm verileri" \
            + " sunmuyor olma ihtimali yüksek.\n"
    
    covidtext += choose_one(LIST_CORONA)
    
    context.bot.send_message(chat_id, covidtext, isgroup=chat_is_group)
    
    if case != (active + deaths + recoveries):
        logger.warning(f"COVID stats didn't add up for {location}.")
        
        notify_admins(
            context,
            f"{location} bölgesi için COVID vakaları tutarsız çıktı!"
        )
        
        context.bot.send_message(
            chat_id,
            f"bu arada farkettim de {get_first_key(DICT_LOCATIONS, location)}"
            " sayıları tutmuyor. belki istisnai bir durum falan vardır. ya da"
            " kaynak yamuktur. ya da dört işlem yapmayı beceremiyorumdur.",
            isgroup=chat_is_group
        )


# TODO: Handle Telegram exceptions better - see:
#   https://github.com/python-telegram-bot/python-telegram-bot/wiki/Exception-Handling
#   https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#an-good-error-handler
def error_log(update, context):
    """Log errors caused by updates."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')


# TODO: Natural lang. proc. for this command too?
# IDEA: (When implemented) Buttoned subscription choice instead of toggling:
#   Instead of switching between states for each user, just execute the routine
#   according to the selected button (if possible).
#   See:
#   https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#keyboard-menus
#   for the keyboard menu implementation.
def annc_subscription(update, context):
    """Toggles a chat ID's subscription to the announcements sent by the bot.
    
    The chats who wish not to receive announcements are "blacklisted".
    """
        
    chat_id = update.effective_chat.id
        
    if chat_id not in db_chats:
        # (This if block is not needed but checking anyway to avoid a redundant
        #   func. call:)
        db_add(PATH_CHATS, db_chats, chat_id)
    
    if chat_id in db_annc_blist:
        db_remove(PATH_ANNC_BLIST, db_annc_blist, chat_id)
        update.message.reply_text(
            "tamamdır, bu konuşmayı duyuru listesine ekledim. fikrinizi"
            " değiştirirseniz bu komutu tekrar çalıştırın. umarım duyuracak bir"
            " şeyler bulabilirim."
        )
    else:
        db_add(PATH_ANNC_BLIST, db_annc_blist, chat_id)
        update.message.reply_text(
            "tamamdır, bu konuşmayı duyuru listesinden çıkardım. fikrinizi"
            " değiştirirseniz bu komutu tekrar çalıştırın."
        )
        
    # Manual backup of the updated chat data. Change if becomes too
    #   overwhelming:
    db_backup(update, context, called_with_message=False)


def announce(update, context):
    """Initiates the chat state for sending an announcement.
    
    Can only be called manually using the /duyur or /announce command by an
    administrator user. However, the chat need not be an admin. chat.
    
    The later announcement sending states are meant to be carried out by
    read_incoming. See the dispatching block in read_incoming for the
    implementation.
    """
    
    chat_id = update.effective_chat.id
    
    if update.effective_user.id not in DB_ADMIN_CHATS:
        update.message.reply_text("yalnızca adminler duyuru yapabilir!")
        return
    
    # Check if there is an ongoing process:
    try:
        state = dict_chat_states[chat_id]
        
        if state.startswith("announce"):
            update.message.reply_text(
                "yarım kalan bir duyuru işi var! önce onu tamamla veya iptal"
                " et."
            )
        else:
            update.message.reply_text(
                "yarım kalan başka bir iş var! önce onu tamamla veya iptal et."
            )
        
        return
    except KeyError:
        pass
    
    dict_chat_states[chat_id] = "announce_lv1"
    
    update.message.reply_markdown_v2(
        "DİKKAT: bu mesajdan sonra gördüğüm ilk mesajı *bütün* bilinen"
        " kullanıcılara duyuru olarak yollayacağım\!\n"
        "/iptal ile iptal edebilirsiniz\.\n"
        "yanlışlıkla gönderilen bir duyuruyu /duyurusil ile geri çekmeyi"
        " deneyebilirsiniz, fakat mesajı bütün alıcılardan silmenin kesin"
        " garantisi yoktur\! dikkatli olunuz\."
    )


def revoke_announcement(update, context):
    """ Deletes the latest announcement's messages.
    
    Only an administrator user can call this function. However, the chat need
    not be an admin. chat.
    """
    
    # TODO: Should shorten redundant update member accesses
    
    if update.effective_user.id not in DB_ADMIN_CHATS:
        update.message.reply_text("yalnızca adminler duyuruları silebilir!")
        return
    
    global dict_last_anncs
    
    logger.info("Starting deletion of latest announcement messages...")
    
    if not dict_last_anncs:
        context.bot.send_message(
            update.effective_chat.id,
            "son duyuru mesajları listesi boş, silebileceğim bir mesaj yok.",
            isgroup=(update.effective_chat.type != "private")
        )
        
        logger.info("Empty message list - Terminating deletion function.")
        
        return
        
    del_msg = context.bot.delete_message
    all_deleted = True
    
    context.bot.send_message(
        update.effective_chat.id,
        "son duyuru mesajını tüm alıcılardan geri çekmeye çalışıyorum...",
        isgroup=(update.effective_chat.type != "private")
    )
    
    for chat_id in dict_last_anncs:
        msg_id = dict_last_anncs[chat_id]
        try:
            if del_msg(chat_id, msg_id):
                logger.info(
                    f"Deleted message (ID {msg_id}) from chat {chat_id}."
                )
            else:
                raise TelegramError
        except TelegramError:
            logger.warning(
                f"Could not delete message (ID {msg_id}) from chat {chat_id}!"
            )
            
            notify_admins(
                context,
                f"{msg_id} no.lu mesaj {chat_id} no.lu konuşmadan silinemedi!"
            )
            
            all_deleted = False
    
    logger.info("Finished deletion of latest announcement messages.")
    
    # Empty the dict
    dict_last_anncs = dict()
    
    if all_deleted:
        context.bot.send_message(
            update.effective_chat.id,
            "mesajlar tüm alıcılardan başarıyla silindi.",
            isgroup=(update.effective_chat.type != "private")
        )
    else:
        context.bot.send_message(
            update.effective_chat.id,
            "mesajlar bir veya daha fazla alıcıdan başarıyla silinemedi. mesaj"
            " zaten alıcı tarafından silinmiş veya son duyurunun üzerinden"
            " silmeyi engelleyecek kadar uzun bir süre geçmiş olabilir.",
            isgroup=(update.effective_chat.type != "private")
        )
    
    logger.info("Emptied last announcements dict. Exiting revoke_announcement.")


def abort_state(update, context):
    """Cancels the state of a chat ID by removing it from dict_chat_states.
    
    The user is informed about the cancellation status.
    """
    
    chat_id = update.effective_chat.id
    reply_with = update.message.reply_text
    
    try:
        state = dict_chat_states[chat_id]
        
        if state.startswith("announce"):
            if update.effective_user.id in DB_ADMIN_CHATS:
                del dict_chat_states[chat_id]
                
                try:
                    del dict_annc_temp[chat_id]
                except KeyError:
                    pass
                
                reply_with("tamamdır, duyuru işlemini iptal ettim.")
            else:
                reply_with("yalnızca adminler duyuru işlemini iptal edebilir!")
        else:
            # Should never execute - ensure all possible states are checked
            del dict_chat_states[chat_id]
            
            reply_with(
                "benimle yürüttüğün bir işlem vardı ama ne olduğunu tam"
                " çıkaramadım. yine de iptal ettim. nolur nolmaz."
            )
            
            logger.warning(f"abort_state aborted unknown state: {state}")
            
            notify_admins(
                context,
                f"bilinmeyen state iptal edildi: {state}"
            )
            
    except KeyError:
        reply_with("iptal edilecek bir şey yok ki")


def main():
    """Starts the bot."""
    
    # TODO: Handle network errors, see:
    #   https://github.com/python-telegram-bot/python-telegram-bot/wiki/Handling-network-errors
    # TODO: Multithreading can be implemented for performance. See:
    #  https://github.com/python-telegram-bot/python-telegram-bot/wiki/Performance-Optimizations
    
    # Increase the connection pool size to 8 (Check telegram/ext/updater.py for
    #   pool size requirements):
    req = Request(con_pool_size=8)
    # Set a limit of 29 messages per second (30 is the max. allowed, 29 should
    #   ensure safety) for all chats, 19 per minute for groups (20 is maximum).:
    msgq = mq.MessageQueue(all_burst_limit=29, group_burst_limit=19)
    skiwobot = SanalkiwoBot(TOKEN, request=req, msg_queue=msgq)
    updater = UpdaterBotStop(bot=skiwobot, use_context=True)
    dp = updater.dispatcher
    jobq = updater.job_queue
    
    # On command messages: #
    dp.add_handler(CommandHandler({"start", "basla", "baslat"}, start))
    dp.add_handler(CommandHandler({"help", "yardim", "info"}, help_info))
    dp.add_handler(
        CommandHandler({"corona", "covid", "covid19", "korona"}, corona)
    )
    dp.add_handler(
        CommandHandler({"abonelik", "subscription"}, annc_subscription)
    )
    dp.add_handler(CommandHandler({"db_backup"}, db_backup))
    dp.add_handler(CommandHandler({"duyur", "announce"}, announce))
    dp.add_handler(CommandHandler({"iptal", "abort"}, abort_state))
    dp.add_handler(
        CommandHandler({"duyurusil", "revokeannc"}, revoke_announcement)
    )
    
    # On non-command updates: #
    # Text messages which do not solely consist of commands and ignores
    #   edits:
    dp.add_handler(
        MessageHandler(
            (Filters.text & (~Filters.update.edited_message)),
            read_incoming
        )
    )
    # (use different Filters attributes to associate message edits and other
    #   types of messages with different func.s)
    
    # Log all errors:
    dp.add_error_handler(error_log)
    
    # Clean leftover files once a day with db_cleanup func.:
    # TODO: JobQueue might benefit from a better implementation. see:
    #   https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions-%E2%80%93-JobQueue
    jobq.run_repeating(db_cleanup, interval=dt.timedelta(days=1), first=0)
    
    # Start the bot:
    if DEPLOYED:
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN
        )
        
        updater.bot.set_webhook("https://sanalkiwobot.herokuapp.com/" + TOKEN)
    else:
        updater.start_polling()
    
    logger.info("Waiting for input...")
    
    # Run the bot until the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

# TODO: Should the globals be defined inside the "if name == main" block?

# Deduce if the program is run locally or is deployed (currently on Heroku):
DEPLOYED = bool(os.environ.get("DEPLOYED", default=False))

# Enable logging:
# IDEA: May keep the logs in a file with level logging.DEBUG
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


## Strings ##

# Constants for paths to database directories and text files #

PATH_CACHE_DIR = ".cache/"
PATH_CHAT_DATA_DIR = "resources/chat_data/"
PATH_COVID_DIR = "resources/covid_data/"

# Text lists:
PATH_TL_DIR = "resources/text_lists/"

# Message text lists:
PATH_ML_DIR = "resources/msg_texts/"

PATH_CHATS = PATH_CHAT_DATA_DIR + "chats.txt"
PATH_ADMIN_CHATS = PATH_CHAT_DATA_DIR + "admin_chats.txt"

# Announcement Blacklist path for those who don't want to be announced:
PATH_ANNC_BLIST = PATH_CHAT_DATA_DIR + "annc_blist.txt"

PATH_TOKEN = "resources/.token.txt"

# Token constant:
if DEPLOYED:
    TOKEN = os.environ.get("TOKEN")
else:
    TOKEN = db_read(PATH_TOKEN, str)

# Bot's ID to use in identity checks:
# FIXME: Make this general for each bot account!
BOT_ID = 1037880552

# Change port if on server (heroku):
if DEPLOYED:
    PORT = int(os.environ.get("PORT", "8443"))

# Last succesful COVID data retrieval date. Initial value is a date guaranteed
#   to compare old enough to re-retrieve (update) a file.
last_covid_get_date = dt.datetime.now() - dt.timedelta(hours=8)


# IDEA: Use below if stickers are implemented. For sticker & media replies, see:
#    https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#working-with-files-and-media
## IDs of some stickers ##

# May create a sticker dictionary and import such data from an external file
# stk_naberhaci = "CAACAgQAAxkBAAEBCCxfCjbXCSWzeI7uJbrN3JqA48ZgfQACiwEAApWp6QFMdCRBHrIkMRoE"


## Sets ##

# Set of the chats which can use the administrative functions of the bot:
DB_ADMIN_CHATS = db_read(PATH_ADMIN_CHATS, read_int=True)

# Sets of chat ID databases: #

db_chats = db_read(PATH_CHATS, read_int=True)
db_annc_blist = db_read(PATH_ANNC_BLIST, read_int=True)

# Sets of few basic Turkish and English words: #
#   "ws" prefix of the variables stand for "word set".
# TODO: Add better suffix detection, maybe through another function? remove the
#   suffixed versions of words from the sets when implemented

WS_GREET = db_read(PATH_TL_DIR + "ws_greet.txt")
WS_WHATSUP = db_read(PATH_TL_DIR + "ws_whatsup.txt")

# Words indicating a message targeted at a group:
WS_GROUP = db_read(PATH_TL_DIR + "ws_group.txt")

# Words indicating a message targeted at the bot, doesn't include "kıvanç" and
#   "kivanc" intentionally:
WS_KIWO = db_read(PATH_TL_DIR + "ws_kiwo.txt")

# Word list for /corona:
WS_CORONA = db_read(PATH_TL_DIR + "ws_corona.txt")

# Words that may indicate a request:
WS_REQUEST = db_read(PATH_TL_DIR + "ws_request.txt")


## Dict.s ##

# Turkish location names with correspondents in COVID datasheet
# The most preferred Turkish name must be the top one if multiple ones exist!
# (get_first_key is used when choosing the Turkish name to use in a reply. see
#   corona function.)
# TODO: Add Taiwan
DICT_LOCATIONS = db_read(PATH_TL_DIR + "dict_locations.txt", dict)

# Chat states: If a chat is in an interactive process requiring more than one
#   interaction with the bot, holds a string representing the process with the
#   chat ID as the key. When the chat sends a message, read_incoming will behave
#   according to the chat's state.
# (Not backing up the data in a file as the states usually last less than a
#   minute or so.)
dict_chat_states = dict()

# Copies of the last sent announcement: Keys are chat IDs and values are message
#   IDs. Kept for the possibility of the need for deletion. No database file
#   correspondent exists.
dict_last_anncs = dict()

# Temporary buffer for announcement message: Keys are chat IDs and values are
#   the announcement messages.
dict_annc_temp = dict()


## String lists to choose one from ##

# "What's up?" replies:
LIST_WHATSUP_REPLY = db_read(PATH_TL_DIR + "list_whatsup_reply.txt", list)

# /corona bonus end-text replies:
LIST_CORONA = db_read(PATH_TL_DIR + "list_corona.txt", list)


## Message strings (for some specific replies) ##

with open(PATH_ML_DIR + "msg_start.txt") as fl:
    MSG_START = fl.read()

with open(PATH_ML_DIR + "msg_help.txt") as fl:
    MSG_HELP = fl.read()


if __name__ == '__main__':
    main()
