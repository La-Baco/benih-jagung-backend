# Aplikasi Laravel untuk VPS. Versi PHP mengikuti Tabel 3.11 (8.3).
FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist --no-interaction
COPY . .
RUN composer dump-autoload --optimize --no-dev

FROM php:8.3-apache

RUN docker-php-ext-install pdo_mysql \
    && a2enmod rewrite headers \
    && sed -ri 's#/var/www/html#/var/www/html/public#g' /etc/apache2/sites-available/000-default.conf \
    && printf '<Directory /var/www/html/public>\n    AllowOverride All\n</Directory>\nServerTokens Prod\nServerSignature Off\n' \
        > /etc/apache2/conf-enabled/laravel.conf

# Satu foto maksimal 10 MB (Tabel 3.12). Unggahan dataset admin bisa berisi 20 foto sekaligus.
# Model .keras diunggah per potongan 8 MB, jadi tidak butuh batas yang lebih besar.
RUN printf 'upload_max_filesize = 10M\npost_max_size = 60M\nmax_file_uploads = 20\nmemory_limit = 256M\nmax_execution_time = 120\nexpose_php = Off\n' \
        > /usr/local/etc/php/conf.d/unggah.ini \
    && cp /usr/local/etc/php/php.ini-production /usr/local/etc/php/php.ini

WORKDIR /var/www/html
COPY --from=vendor /app /var/www/html
RUN php artisan storage:link \
    && chmod +x mulai_server.sh

CMD ["./mulai_server.sh"]
