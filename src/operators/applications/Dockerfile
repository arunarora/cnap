FROM python:3.14

# 1. Create a non-root user 'appuser' with UID 1000
# -m creates a home directory; -u 1000 is a standard UID for many systems
RUN useradd -u 1000 -m appuser

# 2. Set up application directory and adjust ownership
WORKDIR /app
RUN chown -R appuser:appuser /app

# 3. Switch to the non-root user
USER appuser

# Add the local user's bin directory to the system PATH
ENV PATH="${PATH}:/home/appuser/.local/bin"

# 4. Install kopf using pip
RUN pip install --user kopf

# 5. Copy the application code into the container
ADD /src/* /app/

# 6. Set the default command to run the operator
RUN echo $PATH
CMD kopf run /app/operator-applications.py --verbose