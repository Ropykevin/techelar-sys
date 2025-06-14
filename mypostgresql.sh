#!/bin/bash

# Exit on error
set -e

# Variables
DB_NAME="techelar_db"
DB_USER="techelar"
DB_PASSWORD="techelar254!"
HOST="localhost"
PORT="5432"
DOMAIN="tech_courses.techelar.co.ke"
EMAIL="admin@${DOMAIN}"  # Change this if needed
NGINX_CONF_PATH="/etc/nginx/sites-available/${DOMAIN}"

echo "Creating PostgreSQL database and user..."

# Create DB and user
sudo -i -u postgres psql <<EOF


DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '${DB_USER}') THEN
      CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
   END IF;
END
\$\$;

CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF

# Output credentials
echo ""
echo "✅ PostgreSQL user and database created."
echo "🔑 Password: ${DB_PASSWORD}"
echo "🔗 URL: postgresql://${DB_USER}:${DB_PASSWORD}@${HOST}:${PORT}/${DB_NAME}"

# Create Nginx config
echo "Setting up Nginx for domain ${DOMAIN}..."
# give permission to the nginx sites-available directory
sudo chmod -R 775 /etc/nginx/sites-available

sudo bash -c "cat > ${NGINX_CONF_PATH}" <<EOL
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:5010;  
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOL

# Enable site
sudo ln -sf ${NGINX_CONF_PATH} /etc/nginx/sites-enabled/

# Reload Nginx
echo "Reloading Nginx..."
sudo nginx -t && sudo systemctl reload nginx

# Install Certbot and get SSL cert
echo "Installing Let's Encrypt SSL certificate..."
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos -m ${EMAIL}

# Final Nginx reload
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo ""
echo "🎉 Setup complete for ${DOMAIN} with SSL and database access."
