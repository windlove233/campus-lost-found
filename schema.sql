CREATE TABLE IF NOT EXISTS found_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    photo_name VARCHAR(100) NOT NULL,
    description VARCHAR(500) NULL,
    found_on DATE NULL,
    found_area VARCHAR(100) NULL,
    photo_clues JSON NOT NULL,
    image_embedding VARBINARY(2048) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_found_photo (photo_name),
    CONSTRAINT ck_found_embedding CHECK (OCTET_LENGTH(image_embedding) = 2048)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS lost_reports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tracking_token_hash BINARY(32) NOT NULL,
    description VARCHAR(500) NOT NULL,
    lost_on DATE NULL,
    lost_area VARCHAR(100) NULL,
    text_embedding VARBINARY(2048) NOT NULL,
    best_found_item_id BIGINT UNSIGNED NULL,
    best_score DOUBLE NULL,
    ranker_version VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uq_lost_tracking_token (tracking_token_hash),
    KEY idx_lost_active (closed_at, id),
    CONSTRAINT fk_lost_best_found FOREIGN KEY (best_found_item_id) REFERENCES found_items (id),
    CONSTRAINT ck_lost_description CHECK (CHAR_LENGTH(TRIM(description)) > 0),
    CONSTRAINT ck_lost_embedding CHECK (OCTET_LENGTH(text_embedding) = 2048),
    CONSTRAINT ck_lost_best CHECK ((best_found_item_id IS NULL) = (best_score IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS match_notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    lost_report_id BIGINT UNSIGNED NOT NULL,
    found_item_id BIGINT UNSIGNED NOT NULL,
    score DOUBLE NOT NULL,
    ranker_version VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uq_notification_pair (lost_report_id, found_item_id),
    KEY idx_notification_inbox (lost_report_id, read_at, id),
    CONSTRAINT fk_notification_report FOREIGN KEY (lost_report_id) REFERENCES lost_reports (id),
    CONSTRAINT fk_notification_item FOREIGN KEY (found_item_id) REFERENCES found_items (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
