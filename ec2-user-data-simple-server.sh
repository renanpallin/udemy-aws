#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>🎉 PARABÉNS! Você criou sua primeira VPC e EC2!</h1>" > /var/www/html/index.html
echo "<p>Esta página está rodando no seu EC2 na sua própria VPC!</p>" >> /var/www/html/index.html
echo "<p>Te aguardo nas próximas aulas!</p>" >> /var/www/html/index.html
echo "<p>Ass: Renan Pallin</p>" >> /var/www/html/index.html
echo "<p>Data: $(date)</p>" >> /var/www/html/index.html