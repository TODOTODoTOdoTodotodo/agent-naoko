# 샘플 프로젝트 기획서: 사용자 프로필 관리 시스템

## 1. 개요
사용자의 기본 정보를 조회하고 수정하는 간단한 REST API를 구축한다.

## 2. 요구사항

### 2.1 데이터 모델 (User)
- `id`: Long (PK, Auto Increment)
- `username`: String (Unique, 필수)
- `email`: String (필수, 이메일 형식)
- `bio`: String (선택, 최대 500자)

### 2.2 기능 명세
1.  **사용자 조회 (GET /api/users/{id})**
    - 성공 시: 200 OK, User 정보 반환
    - 실패 시: 404 Not Found

2.  **사용자 생성 (POST /api/users)**
    - 입력: username, email, bio
    - 성공 시: 201 Created, 생성된 User ID 반환
    - 실패 시: 400 Bad Request (유효성 검증 실패)

### 2.3 제약 사항
- Spring Boot 스타일의 구조를 따를 것 (Controller, Service, Repository).
- h2 database를 사용할 것.
- Lombok을 사용할 것.
