# DockerREADME

## Building and Running the Docker Container

This guide explains how to build and run the Docker container for this project, both locally and on a remote VM (e.g., whitemountain server).

---

## Prerequisites
- Docker must be installed on your machine or VM.
- You must have access to the project files (including Dockerfile and requirements.txt).
- For remote VM: You need SSH access and Docker installed on the VM.

---

## Local Build & Run

### 1. Build the Docker Image
First, make sure Docker is installed on your device, and is open and running currently.

Open a terminal and cd into root directory root (where the Dockerfile is located) and run:

```
docker build -t syllabus-checker .
```
- This command builds the Docker image and names it `syllabus-checker`.
- You will have to wait a moment for docker to install the required dependencies listed in the requirements file.

### 2. Run the Docker Container
To run the container and expose port 8001 (Flask default):

```
docker run -p 8001:8001 chatbot-container
```
- This maps port 8001 in the container to port 8001 on your host.
- Access the app at [http://localhost:8001](http://localhost:8001)

---

## Running on Whitemount VM (in review currently!)

### 1. Transfer Project Files
- Use `scp` or SFTP to copy your project folder (including Dockerfile) to the VM.
- Example:
  ```
  scp -r /path/to/project username@whitemountain:/home/username/project
  ```

### 2. SSH into the VM
```
ssh username@whitemount.sr.unh.edu
```

### 3. Build the Docker Image on the VM
Navigate to your project directory:
```
cd /home/username/project
```
Build the image:
```
docker build -t chatbot-container .
``` 

### 4. Run the Docker Container on the VM
```
docker run -p 8001:8001 chatbot-container
```
- If you want the app accessible from outside the VM, ensure firewall rules allow traffic to port 8001.
- Access the app at `http://whitemount:8001` (or use the VM's IP address).

---

## Notes
- If you change requirements.txt or Dockerfile, rebuild the image.
- 
- You may need to run Docker commands with `sudo`:
  ```
  sudo docker build -t chatbot-container .
  sudo docker run -p 8001:8001 chatbot-container
  ```


---

## Troubleshooting
- If you see missing package errors, check requirements.txt and rebuild.
- If the container won't start, check logs with:
  ```
  docker logs <container_id>
  ```
- For port conflicts, use a different host port: `-p 8080:8001`

---

## Useful Commands
- List images: `docker images`
- List running containers: `docker ps`
- Stop a container: `docker stop <container_id>`
- Remove a container: `docker rm <container_id>`
- Remove an image: `docker rmi <image_id>`

---

## Contact
For further help, contact the project maintainer or your system administrator.
