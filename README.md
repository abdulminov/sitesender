Проект разварачивается на Vagrant + Podman. используется Ansible для конфигурации узлов.

Application Layer (Nodes): 
master: ---
workers: Стек VK-бота и Django на базе Rootless Podman, развернутый с помощью Ansible.
Infrastructure as Code (IaC)

Vagrant: Автоматическое создание изолированной сети из Master и Worker нод (Ubuntu) для симуляции реального дата-центра.
Ansible:
prepare_nodes.yml: Подготовка системы под Rootless Podman (настройка lingering, subuid/subgid).
deploy_app.yml: Деплой контейнеров с использованием переменных окружения и зашифрованных секретов (Ansible Vault).
Security Hardening
Privilege Drop: Контейнеры лишены всех системных привилегий (cap_drop: [ALL]).
Identity: Сервисы внутри контейнеров работают от не-привилегированных пользователей.
