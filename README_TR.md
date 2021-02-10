# Sanal Kiwo[^1]

*Yapım aşamasında, gerçekçi bir Telegram muhabbet botu*

[Yazışmayı deneyin!](https://t.me/sanalkiwobot)

---

![(Click here for the English manual.)](./README.md)

Botun esas özelliği "/" ile başlayan komutların yanısıra normal mesajlardan da bir komut çağrısını anlamaya çalışmasıdır. Bütün yazılı mesajlar "read_incoming" ("geleni oku") isimli bir yönlendirici fonksiyona gönderilir. Eğer mesajda anahtar kelimelere rastlanırsa, uygun işlem yürütülür.
Bot bu yöntemi basit konuşmalara yanıt verebilir veya komutlarından birini çağırabilir.

Using this method, the bot can reply to some chatting prompts or call one of its commands.

### Komutlar:

* **/baslat** veya (**/start**) botu başlatır ve bir açılış mesajı gönderir.
* **/yardim** veya (**/help**) botun özelliklerini açıklayan bir bilgilendirme mesajı gönderir.
* **/corona** bir veya daha fazla ülkenin günlük COVID-19 verilerini [bu kaynaktan](https://github.com/CSSEGISandData/COVID-19) alır ve sunar.
* **/abonelik** (veya **/subscription**) bir yazışmanın yöneticilerden gelebilecek otomatik duyurulara aboneliğini ayarlar.
* **/iptal** (veya **/abort**) bot ile kullanıcı arasında birden fazla mesajlık bir "diyalog" sürüyorsa bunu iptal eder. Yani, eğer konuşmaya atanan bir "hal" varsa, bu "hal" temizlenir. (Şu anda yönetici olmayan kullanıcıların bot ile girebileceği birden fazla mesajlı bir diyalog bulunmamaktadır.)

#### Yönetici (Admin) komutları:

* **/db_backup** `resources/chat_data/` dizininin yedeğini yönetici(ler)e gönderir.
* **/duyur** (veya **/announce**) çağıran admin ile bot arasında bir diyalog başlatır. Admin bu diyaloğu takip ederek botun duyurulara abone olan bütün kullanıcılarına bir duyuru mesajı gönderebilir. Gönderen kişiden duyuruyu göndermeden önce teyit etmesi istenir.
* **/duyurusil** (veya **/revokeannc**) son duyurunun mesajlarını bütün kullanıcılardan silmeye çalışır. Bu komut yanlışlıkla gönderilen bir duyuru mesajı durumunda son çare olarak kullanılabilir.

## GEREKENLER

Python 3.6 veya daha yüksek bir sürüm gereklidir.

Gereken modüller:

* emoji *([Bu](https://github.com/carpedm20/emoji/tree/d73e3063e30bbce8cdbab873a57e4fdef1bf7c12) sürüm kullanılmaktadır ve `requirements.txt` dosyasında bu sürüm yer almıştır, daha sonraki sürümler ile test edilmemiştir.)*
* pandas (1.0.3)
* python-telegram-bot (12.8)
* requests (2.21.0)

## SETUP

**1)** Gereken modülleri kurunuz. `pip`/`pip3` komutlarından birini kullanabilirsiniz:

```
pip install -r requirements.txt
```

**2)** Bot için [bir hesap yaratın](https://core.telegram.org/bots#3-how-do-i-create-a-bot) ve bot'un token'ini alın.

**3)** Eğer botu bir hosting sitesinde (örn. Heroku, Glitch...) kullanacaksanız, `DEPLOYED` ve `TOKEN` isimli ortam değişkenlerini yaratın. `DEPLOYED`ı `True`ya, `TOKEN`i bot tokeninize karşılık gelecek şekilde ayarlayın.

Eğer botu lokal olarak çalıştırmak istiyorsanız, ortam değişkenlerini ayarlamanıza gerek yoktur. Token'i kurmak için `resources/.token.txt` dosyasını sadece botun token'ini içerecek şekilde tekrar yazınız.

**4)** Eğer herhangi bir grup yazışmasını veya özel yazışmayı yönetici olarak ayarlamak isterseniz, öncelikle bu yazışmaların ID'lerini edinmeniz gerekir. Botun henüz bunun için bir fonksiyonu yoktur, fakat çeşitli yöntemler mevcuttur:

* [@get_id_bot](https://telegram.me/get_id_bot)'u kullanmak.

* `https://api.telegram.org/botXXXXXX/getUpdates` adresini `XXXXXX`i botun token'i ile değiştirip ziyaret etmek, istenen yazışmadan bir mesaj atmak ve sayfayı yenilemek. Yazışma ID'si `result -> 0 -> message -> chat -> id` altında görülebilir.

*`read_incoming` fonksiyonuna geçici olarak `update.message.chat.id` değerini gösteren kod eklemek, botu çalıştırmak (bkz. 5. aşama) ve istenen yazışmadan bir mesaj göndermek.

ID'leri elde ettikten sonra her biri ayrı bir satıra gelecek şekilde `resources/chat_data/admin_chats.txt` dosyasına yazınız.
Boş satırlar ve `#%#` ile başlayan satırlar okunmadan geçilecektir. Aşağıdaki örnekler geçerlidir:

```
1111111
-2222222
3333333
```

```
#%# Adminler grubu:
-1111111

#%# Kullanıcı 1:
2222222
```

**5)** Botu istediğiniz hosting servisinde veya lokal olarak çalıştırın:

```
$ python sanalkiwobot.py
```

## NOTLAR

`sanalkiwobot.py` içinde özel yorum çeşitleri bulunur:

* `FIXME` yorumları doğru çalışmayan ve en kısa sürede düzeltilmesi gereken bir özelliği gösterir.
* `TODO` yorumları planlanan iyileştirmeleri ve yeni özellikleri gösterir.
* `IDEA` yorumları botun çalışması için yüksek önem arz etmeyen yeni özellik önerilerini gösterir.
* `NOTE` yorumları geliştirme esansında akılda bulundurulacak nispeten önemli bilgileri içerir.

Kod İngilizce yazılmıştır, fakat bot Türkçe dilinde çalışmaktadır. Tam İngilizce çeviri ve dil seçeneği geliştirme aşamasındadır.

## LİSANS

Bu program MIT License ile lisanslanmıştır. Daha fazla bilgi için `LICENSE` isimli dosyayı inceleyiniz.

---

[^1]: Botun benim yazışma şeklimi taklit edecek şekilde tasarlandığı söyleyebilir. İsmini kendi adımdan (Kıvanç) alıyor.
