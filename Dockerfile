FROM alpine

COPY theme.js /theme.js

RUN mkdir -p /app/dist/assets/

VOLUME /app/dist/assets/

ENTRYPOINT ["cp", "-v", "/theme.js", "/app/dist/assets/theme.js"]
