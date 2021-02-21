# Super Simple Jenkins Viewer

This project is a super simple Jenkins front end.

It's meant to shield your Jenkins server from potential security issues.

Don't forget to block the internal Jenkins port with a firewall and bind only to localhost for good measure!

[Live demo](https://jenkins.dries007.net)

## Deployment info

More for myself than a recommendation.
This assumes a few things about the runtime environment:
- Use Arch Linux (nginx user:group is http:http instead of www-data:www-data).
- Use nginx on the host as a proxy.
- Use (sub)domains to differentiate between different apps (or have nginx do the url-rewriting).
- The nginx worker user is http, the `/run/sock` folder can be used with 1 subfolder per app/subdomain.
- Jenkins is bound to 127.0.0.1:8090. This means need to run with `--network host` to avoid dealing with routing from the container to the host but still not allow external access to jenkins.  

Here is my startup command:

```
docker run -d --name jenkinsviewer -v /run/sock/jenkins:/sock -e RUNAS=$(id -u http):$(id -g http) --network host --restart unless-stopped ghcr.io/dries007/jenkinsviewer:latest
```

The nginx config is roughly based on previous configs of mine and [the gunicorn example](https://docs.gunicorn.org/en/stable/deploy.html). This is the important bits:

```
user http http;
http {
    include mime.types;
    sendfile on;
    server {
        listen 80 deferred;
        server_name jenkins.dries007.net; 
        keepalive_timeout 5;
        location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            # we don't want nginx trying to do something clever with
            # redirects, we set the Host: header above already.
            proxy_redirect off;
            proxy_pass unix:/run/sock/jenkins/web.sock;
        }
    }
}
```

