# SiteSender — DevOps-проект для лабораторной практики

Персональный DevOps-проект, демонстрирующий автоматизацию CI/CD, развёртывание приложений в контейнерах, автоматизацию с помощью Ansible, проверки работоспособности и откат к последнему стабильному образу приложения.

## Обзор проекта

SiteSender — веб-приложение и бот, развёрнутые на отдельных узлах Linux. Основная цель проекта — построить воспроизводимый процесс развёртывания и автоматизировать обработку ошибок, возникающих при деплое.

Пайплайн CI/CD собирает образы контейнеров и публикует их в GitHub Container Registry (GHCR). Ansible развёртывает необходимые компоненты приложения на целевых узлах с использованием rootless Podman и `podman-compose`.

Если новая версия приложения не проходит проверку работоспособности после развёртывания, роль Ansible пытается восстановить предыдущую успешно развёрнутую версию образа.

## Архитектура

В лабораторной среде используются отдельные узлы для веб-приложения и бота.

- **Master-узел:** Django-приложение, база данных PostgreSQL и Nginx.
- **Worker-узел:** приложение бота на Python, построенное на FastAPI и Uvicorn.
- **Реестр контейнеров:** GitHub Container Registry (GHCR).
- **CI/CD:** GitHub Actions с собственным self-hosted runner.
- **Управление конфигурацией и развёртыванием:** Ansible.
- **Среда выполнения контейнеров:** rootless Podman с `podman-compose`.
- **Управление сервисами:** пользовательский сервис systemd.

### Общая последовательность работы

1. Изменения в коде отправляются в GitHub.
2. GitHub Actions определяет, какие компоненты приложения необходимо собрать и развернуть.
3. Пайплайн собирает соответствующий образ контейнера и публикует его в GHCR с версионным тегом.
4. Ansible развёртывает соответствующий компонент на целевом узле.
5. Контейнер приложения запускается, после чего проверяется его работоспособность.
6. Если проверка проходит успешно, версия развёрнутого образа сохраняется как последняя стабильная версия.
7. Если проверка завершается ошибкой, роль Ansible пытается восстановить ранее сохранённую стабильную версию образа.

## Пайплайн CI/CD

Workflow GitHub Actions автоматизирует сборку образов, их публикацию и развёртывание.

Основные возможности:

- Условная сборка и развёртывание в зависимости от изменённых путей в репозитории.
- Отдельные образы контейнеров для веб-приложения и бота.
- Версионные теги образов, связанные с запусками workflow GitHub Actions.
- Публикация образов в GHCR.
- Автоматическое развёртывание в соответствующую группу узлов из инвентаря Ansible.
- Развёртывание изменений только в инфраструктурной конфигурации без ненужной пересборки образов приложения.

Для образов используется следующий формат имён:

- `ghcr.io/abdulminov/sitesender-web:<tag>`
- `ghcr.io/abdulminov/sitesender-bot:<tag>`

Пайплайн также публикует тег `latest`. Версионные теги позволяют идентифицировать конкретные сборки и выполнять откат к определённой версии.

## Развёртывание с помощью Ansible

Ansible управляет развёртыванием на master- и worker-узлах.

Автоматизация развёртывания включает:

- Подготовку каталогов приложения и файлов конфигурации.
- Аутентификацию в GHCR.
- Генерацию соответствующей конфигурации Compose для каждого узла.
- Управление пользовательским сервисом systemd.
- Запуск контейнеров приложения или их пересоздание.
- Ожидание успешного прохождения проверки работоспособности новым контейнером.
- Сохранение версии образа последнего успешного развёртывания.
- Попытку отката, если новая версия не проходит проверку работоспособности.

Общая роль `app_stack_manager` содержит совместную логику развёртывания, а настройки конкретного узла определяют, какие сервисы должны запускаться на каждом хосте.

## Проверки работоспособности (Health Checks)

В процессе развёртывания используются HTTP-эндпоинты приложения для проверки его базовой доступности.

- **Django:** `/health`
- **Бот:** `/health`

Проверки работоспособности контейнеров выполняются изнутри контейнера и подтверждают, что соответствующий эндпоинт успешно отвечает на запрос.

Ansible периодически проверяет состояние контейнера и продолжает развёртывание только в том случае, если контейнер переходит в состояние `healthy` в пределах заданного количества попыток и временного интервала.

Успешная проверка подтверждает базовую доступность приложения, но не гарантирует корректную работу всех его функций и обработчиков запросов.

## Откат (Rollback)

Для каждого контейнера роль развёртывания поддерживает файл с тегом образа последней успешно развёрнутой версии.

Процесс отката выглядит следующим образом:

1. Развернуть новую версию образа.
2. Дождаться успешного прохождения проверки работоспособности новым контейнером.
3. Если проверка прошла успешно, обновить файл со стабильной версией.
4. Если проверка завершилась ошибкой, прочитать ранее сохранённую стабильную версию.
5. Сформировать конфигурацию Compose с использованием стабильного образа и перезапустить приложение.
6. Проверить работоспособность восстановленного контейнера.
7. Пометить развёртывание как неудачное, даже если откат прошёл успешно, чтобы ошибка новой версии оставалась видимой в результатах CI/CD.

Если стабильная версия ранее не была сохранена, автоматический откат невозможен.

Стабильная версия — это последняя версия, развёртывание которой прошло настроенную проверку работоспособности. Это не гарантирует отсутствия ошибок во время выполнения приложения.

## Тестирование обработки ошибок

Механизм отката проверялся с помощью намеренно некорректного тега образа, который отсутствовал в GHCR и не мог быть загружен.

Развёртывание новой версии завершилось ошибкой, задача проверки работоспособности исчерпала все попытки, после чего механизм отката в Ansible восстановил ранее сохранённый стабильный образ. Восстановленное приложение успешно прошло проверку работоспособности, при этом общий результат развёртывания остался неудачным, как и предусмотрено логикой пайплайна.

В рамках отдельного теста в стартовый код бота была намеренно внесена синтаксическая ошибка Python. Новый контейнер неоднократно завершал работу до того, как приложение успевало начать отвечать на запросы к эндпоинту проверки работоспособности. Проверка зафиксировала, что контейнер так и не перешёл в состояние `healthy`, что запустило процедуру отката.

Эти тесты демонстрируют восстановление после ошибок развёртывания, препятствующих успешному запуску приложения.

## Ограничения и возможные улучшения

Это учебный проект, ориентированный на практическую автоматизацию развёртывания, а не на создание готовой к промышленной эксплуатации платформы.

Текущие ограничения:

- Проверки работоспособности подтверждают базовую доступность приложения, но не проверяют весь его функционал.
- Ошибки во время выполнения отдельных обработчиков запросов не обязательно приводят к откату, если эндпоинт проверки работоспособности продолжает отвечать успешно.
- Для отката требуется ранее сохранённая стабильная версия образа.
- Автоматизация миграций базы данных и откат миграций не входят в текущую область проекта.
- Мониторинг приложения, оповещения и централизованное наблюдение за состоянием системы в проекте не реализованы.

Возможные направления дальнейшего развития — мониторинг приложения, настройка оповещений и более комплексные интеграционные тесты.

## Продемонстрированные навыки

- Работа с Git и организация процесса разработки на GitHub.
- Построение CI/CD с помощью GitHub Actions.
- Условный запуск этапов пайплайна в зависимости от изменённых путей.
- Сборка образов контейнеров и публикация в GHCR.
- Упаковка приложений с помощью Dockerfile.
- Развёртывание контейнеров с использованием Podman в rootless-режиме.
- Работа с playbook-файлами, ролями, шаблонами, инвентарём и переменными Ansible.
- Настройка пользовательских сервисов systemd.
- Реализация проверок работоспособности приложений и контейнеров.
- Автоматический откат после неудачного развёртывания.
- Диагностика проблем с использованием логов приложений, `journalctl`, Podman и вывода Ansible.

## Цель проекта

Цель проекта — продемонстрировать практические DevOps-навыки путём создания и отладки автоматизированного пайплайна развёртывания, проверки сценариев отказа и реализации восстановления до ранее успешно развёрнутой версии приложения.






# SiteSender — DevOps Lab Project

A personal DevOps project demonstrating automated CI/CD, containerized application deployment, Ansible automation, health checks, and rollback to the last known stable application image.

## Project Overview

SiteSender is a web application and bot deployed on separate Linux nodes. This project focuses on building a repeatable deployment workflow and handling deployment failures automatically.

The CI/CD pipeline builds and publishes container images to GitHub Container Registry (GHCR). Ansible deploys the appropriate application components to the target nodes using rootless Podman and `podman-compose`.

If a new application version fails its deployment health check, the deployment role attempts to restore the previously successful image version.

## Architecture

The lab uses separate nodes for the web application and the bot.

- **Master node:** Django web application, PostgreSQL database, and Nginx.
- **Worker node:** Python bot application built with FastAPI and Uvicorn.
- **Container registry:** GitHub Container Registry (GHCR).
- **CI/CD:** GitHub Actions with a self-hosted runner.
- **Configuration management and deployment:** Ansible.
- **Container runtime:** Rootless Podman with `podman-compose`.
- **Service management:** systemd user service.

### High-level workflow

1. A code change is pushed to GitHub.
2. GitHub Actions determines which application components need to be built and deployed.
3. The pipeline builds the relevant container image and pushes it to GHCR with a versioned tag.
4. Ansible deploys the corresponding component to the target node.
5. The application container starts and its health status is checked.
6. If the health check succeeds, the deployed image version is recorded as the latest stable version.
7. If the health check fails, the deployment role attempts to restore the previously recorded stable image.

## CI/CD Pipeline

The GitHub Actions workflow automates image building, publishing, and deployment.

Key features:

- Conditional builds and deployments based on changed paths.
- Separate web and bot container images.
- Versioned image tags associated with GitHub Actions workflow runs.
- Image publishing to GHCR.
- Automated deployment to the appropriate Ansible inventory group.
- Deployment of infrastructure-only changes without unnecessarily rebuilding application images.

Images follow this naming convention:

- `ghcr.io/abdulminov/sitesender-web:<tag>`
- `ghcr.io/abdulminov/sitesender-bot:<tag>`

The pipeline also publishes a `latest` tag. Versioned tags are used to identify specific builds and support rollback.

## Ansible Deployment

Ansible manages deployment to the master and worker nodes.

The deployment automation includes:

- Preparing application directories and configuration files.
- Authenticating with GHCR.
- Rendering the appropriate Compose configuration for each node.
- Managing the user-level systemd service.
- Starting or recreating application containers.
- Waiting for the new container to pass its health check.
- Recording the last successfully deployed image version.
- Attempting rollback when the new deployment fails its health check.

The common `app_stack_manager` role handles shared deployment logic, while node-specific configuration determines which services run on each host.

## Health Checks

The deployment process uses application health endpoints to verify basic availability.

- **Django:** `/health`
- **Bot:** `/health`

Container health checks run from inside the container and verify that the corresponding endpoint responds successfully.

Ansible polls the container health status and continues the deployment only when the container becomes healthy within the configured retry window.

A successful health check confirms basic application availability. It does not guarantee that every application feature or request handler works correctly.

## Rollback

The deployment role maintains a file containing the image tag of the last successfully deployed version for each container.

The rollback workflow is:

1. Deploy the candidate image.
2. Wait for the candidate container to pass its health check.
3. If the check succeeds, update the stable-version file.
4. If the check fails, read the previously recorded stable version.
5. Render the Compose configuration using the stable image and restart the application.
6. Verify the restored container's health.
7. Mark the deployment as failed even if rollback succeeds, so the failed release remains visible in CI/CD results.

If no stable version has been recorded, automatic rollback is unavailable.

The stable version represents the last deployment that passed the configured health check. It is not a guarantee that the application is free of runtime defects.

## Failure Testing

The rollback mechanism was tested by deploying a deliberately invalid image tag that could not be retrieved from GHCR.

The candidate deployment failed, the health-check task exhausted its retries, and the Ansible rollback handler restored the previously recorded stable image. The restored application passed its health check, while the overall deployment correctly remained marked as failed.

A separate test introduced a Python syntax error into the bot's startup code. The new container repeatedly exited before the application could serve its health endpoint. The deployment health check detected that the container never became healthy, triggering the rollback procedure.

These tests demonstrate recovery from deployment failures that prevent the application from starting successfully.

## Limitations and Future Improvements

This is a learning project focused on practical deployment automation rather than a production-ready platform.

Current limitations include:

- Health checks validate basic availability, not all application functionality.
- Runtime errors in individual request handlers may not trigger rollback if the health endpoint remains healthy.
- Rollback requires a previously recorded stable image.
- Database migration automation and migration rollback are outside the current scope.
- Application monitoring, alerting, and centralized observability are not implemented as part of this project.

Possible future improvements include application-level monitoring, alerting, and more comprehensive integration tests.

## Skills Demonstrated

- Git and GitHub-based development workflow.
- GitHub Actions CI/CD.
- Conditional pipeline execution based on changed paths.
- Container image builds and publishing to GHCR.
- Dockerfile-based application packaging.
- Podman and rootless container deployment.
- Ansible playbooks, roles, templates, inventory, and variables.
- systemd user services.
- Application and container health checks.
- Automated rollback after deployment failure.
- Troubleshooting using application logs, `journalctl`, Podman, and Ansible output.

## Project Goal

The goal of this project is to demonstrate practical DevOps skills by building and troubleshooting an automated deployment pipeline, validating failure scenarios, and implementing recovery to a previously successful application version.
