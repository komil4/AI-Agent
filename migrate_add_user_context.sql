-- Миграция для добавления поля user_context в таблицу users
-- Выполнить этот скрипт для обновления существующих баз данных

-- Добавляем поле user_context в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_context TEXT;

-- Комментарий к полю
COMMENT ON COLUMN users.user_context IS 'Дополнительный контекст пользователя от LLM для сохранения между сессиями';

-- Проверяем, что поле добавлено
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'user_context';
