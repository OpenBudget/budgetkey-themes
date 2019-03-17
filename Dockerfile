FROM alpine

COPY theme.*.json /
COPY main_page.*.json /

RUN mkdir -p /themes

ENTRYPOINT ["cp", "-v", "/theme.*.json", "/themes/"]
