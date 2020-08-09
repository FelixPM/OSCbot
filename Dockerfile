FROM python:3.7-slim

# Install app dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Create app directory
WORKDIR /app

# Bundle app source
COPY . /app

EXPOSE 8080
CMD [ "python", "OSCar.py" ]