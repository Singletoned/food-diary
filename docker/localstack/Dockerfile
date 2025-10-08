FROM localstack/localstack:3.0

# Install additional tools for initialization
RUN pip install awscli-local[ver2]

# Copy initialization scripts
COPY init/ /etc/localstack/init/ready.d/