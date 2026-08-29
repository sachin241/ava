# Local Mobile HTTPS With Nginx

Mobile browsers only enable camera and microphone on a secure origin. `http://192.168.x.x:8000` will usually load the page but block media permissions. Put Nginx in front of Django and open the HTTPS Nginx URL from the phone.

## 1. Run Django Locally

```powershell
python manage.py runserver 127.0.0.1:8000
```

Keep Django bound to localhost. Nginx will expose it on your network.

## 2. Create A Trusted Local Certificate

Recommended: use `mkcert`.

```powershell
mkcert -install
mkcert ava.local 192.168.1.1 192.168.137.1 localhost 127.0.0.1
```

Replace `192.168.1.1` or `192.168.137.1` with your computer's actual LAN or hotspot IP.

For mobile testing, the phone must trust the mkcert root CA. Install the generated root CA on the phone, then enable full trust for it in the phone's certificate settings.

## 3. Install The Nginx Config

Copy `deploy/nginx/ava.conf` into your Nginx sites/config directory.

Update these paths in the config to match where your certificate files live:

```nginx
ssl_certificate /etc/nginx/certs/ava.local.pem;
ssl_certificate_key /etc/nginx/certs/ava.local-key.pem;
```

Then reload Nginx.

```powershell
nginx -s reload
```

## 4. Open From Mobile

Connect the phone and computer to the same Wi-Fi or hotspot. Open:

```text
https://<your-computer-ip>/
```

Then tap `CONNECT CAMERA`, followed by `ENABLE AVA VOICE` or `ASK AVA`.

## 5. Django Environment

If you use a different IP or hostname, set:

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,ava.local,<your-computer-ip>
DJANGO_CSRF_TRUSTED_ORIGINS=https://ava.local,https://<your-computer-ip>
```

Restart Django after changing environment values.
