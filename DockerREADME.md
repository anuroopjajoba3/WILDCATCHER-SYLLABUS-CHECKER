# DockerREADME

## Building and Running the Docker Container

This guide explains how to build and run the Docker container for this project on the vm, but it can be run locally the same way for development.

---

## Prerequisites
- Docker must be installed on your machine or VM.
- You must have access to the project files (including Dockerfile and requirements.txt).
- For remote VM: You need SSH access and Docker installed on the VM.

---

## Build & Run

### 1. SSH into the VM
First, ssh into the vm using your user id
```
ssh username@whitemount.sr.unh.edu
```

### 3. Build the Docker Image on the VM
Navigate to your project directory:
```
cd /home/user/[your user id]/project
```
Build the image:
```
docker build -t syllabus-checker .
```
- This command builds the Docker image and names it `syllabus-checker`.
- the `.` at the end dictates where to build the docker container. `.` means in the working dir
- You may have to wait a moment for docker to install the required dependencies listed in the requirements file.

### 4. Run the Docker Container on the VM
```
docker run -p 8001:8001 syllabus-checker
```
- ensures use of the port 8001 
- Access the app at `https://whitemount-t1.sr.unh.edu` 

## Useful Commands
- List images: `docker images`
- List running containers: `docker ps`
- Stop a container: `docker stop <container_id>`
- Remove a container: `docker rm <container_id>`
- Remove an image: `docker rmi <image_id>`

---

## Notes
- If you change requirements.txt or Dockerfile, rebuild the image.
- If you log out of the vm, the container will still run. use `docker ps` to see all running containers on vm to verify
- if you need to stop the container (to rebuild), use `docker stop [container ID or name]` 
---

## Troubleshooting
- If you see missing package errors, check requirements.txt and rebuild.
- If the container won't start, check logs with:
  ```
  docker logs <container_id>
  ```


