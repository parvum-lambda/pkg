FROM ubuntu:20.04

MAINTAINER "kiske; <maike.704@gmail.com>"

RUN apt update
RUN apt install -y git make

RUN type -p curl >/dev/null || apt install curl -y

# GH CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt update && \
    apt install gh -y

CMD ["/bin/bash", "-c", "echo \"GitHub.com\\ SSH \\Yes \\ \\ lambda-key \\ Login with a web browser \\ \" | gh auth login"]