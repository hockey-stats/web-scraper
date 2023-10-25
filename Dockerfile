FROM ubuntu:18.04 AS base

# Most of these packages are dependencies for chrome and the chromedriver
RUN apt update && apt install -y python3 python3-pip curl unzip wget \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 \
    libnspr4 libnss3 lsb-release xdg-utils libxss1 libdbus-glib-1-2 \ 
    libgbm1 libu2f-udev libvulkan1 xvfb vim

# Installs the chromedriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    wget --no-verbose \ 
    	https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip -d /usr/bin && \
    chmod +x /usr/bin/chromedriver && \
    rm chromedriver_linux64.zip && \
    # Installs Chrome
    wget --no-verbose -O /tmp/chrome.deb \ 
    https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.90-1_amd64.deb && \
    apt install -y /tmp/chrome.deb && \
    rm /tmp/chrome.deb

WORKDIR /home/scraping/
COPY ./scraping .

ENV PYTHONPATH='/home'
RUN pip3 install -r requirements.txt

CMD python3 scrape_team_tables.py
