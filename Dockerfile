FROM alpine

RUN mkdir -p prep
COPY theme.*.json prep/
COPY main_page.*.json prep/

RUN mkdir -p /themes

ENTRYPOINT ["cp", "-v", "prep/*", "/themes/"]
