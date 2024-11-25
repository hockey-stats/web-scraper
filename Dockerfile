FROM ubuntu:24.04

# Most of these packages are dependencies for chrome and the chromedriver
RUN apt update && apt install -y python3 python3-pip curl unzip wget \
    fonts-liberation libappindicator3-1 libasound2t64 libatk-bridge2.0-0 \
    libnspr4 libnss3 lsb-release xdg-utils libxss1 libdbus-glib-1-2 \ 
    libgbm1 libu2f-udev libvulkan1 xvfb vim

# Installs the chromedriver
RUN CHROMEDRIVER_VERSION=131.0.6778.85 &&                                                                                    \
    wget --no-verbose                                                                                                         \ 
    	https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip &&     \
    unzip chromedriver-linux64.zip -d /usr/bin &&                                                                               \
    chmod +x /usr/bin/chromedriver-linux64 &&                                                                                    \
    rm chromedriver-linux64.zip                                                                                            
    
# Installs Chrome                                                                                                              
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - &&                                              \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get -y update  &&                                                                                                                \
    apt-get install -y google-chrome-stable                                                                                            

WORKDIR /home/scraping/
COPY ./scraping .

ENV PYTHONPATH='/home'
RUN pip3 install -r requirements.txt --break-system-packages

CMD python3 scrape_team_tables.py
