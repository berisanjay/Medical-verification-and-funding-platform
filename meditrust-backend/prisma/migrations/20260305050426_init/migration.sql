-- CreateTable
CREATE TABLE `User` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(191) NOT NULL,
    `email` VARCHAR(191) NOT NULL,
    `password_hash` VARCHAR(191) NOT NULL,
    `role` ENUM('PATIENT', 'ADMIN', 'NGO') NOT NULL DEFAULT 'PATIENT',
    `phone` VARCHAR(191) NULL,
    `native_languages` JSON NULL,
    `aadhaar_number` VARCHAR(191) NULL,
    `otp_verified` BOOLEAN NOT NULL DEFAULT false,
    `is_blacklisted` BOOLEAN NOT NULL DEFAULT false,
    `blacklist_reason` VARCHAR(191) NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updated_at` DATETIME(3) NOT NULL,

    UNIQUE INDEX `User_email_key`(`email`),
    UNIQUE INDEX `User_aadhaar_number_key`(`aadhaar_number`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `OTP` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `user_id` INTEGER NOT NULL,
    `email` VARCHAR(191) NOT NULL,
    `otp_code` VARCHAR(191) NOT NULL,
    `purpose` ENUM('REGISTRATION', 'CAMPAIGN_CREATION', 'HOSPITAL_CHANGE', 'ADMIN_LOGIN') NOT NULL,
    `is_used` BOOLEAN NOT NULL DEFAULT false,
    `expires_at` DATETIME(3) NOT NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Hospital` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(191) NOT NULL,
    `city` VARCHAR(191) NOT NULL,
    `state` VARCHAR(191) NOT NULL,
    `pincode` VARCHAR(191) NOT NULL,
    `address` VARCHAR(191) NOT NULL,
    `phone` VARCHAR(191) NULL,
    `email` VARCHAR(191) NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Campaign` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `patient_id` INTEGER NOT NULL,
    `patient_hms_id` INTEGER NULL,
    `hospital_id` INTEGER NULL,
    `patient_full_name` VARCHAR(191) NOT NULL,
    `patient_age` INTEGER NOT NULL,
    `patient_gender` VARCHAR(191) NOT NULL,
    `patient_aadhaar` VARCHAR(191) NOT NULL,
    `patient_city` VARCHAR(191) NOT NULL,
    `patient_state` VARCHAR(191) NOT NULL,
    `patient_languages` JSON NULL,
    `relationship_to_fundraiser` VARCHAR(191) NOT NULL DEFAULT 'SELF',
    `title` VARCHAR(191) NOT NULL,
    `story_original` TEXT NULL,
    `story_gemini` TEXT NULL,
    `story_language` VARCHAR(191) NULL,
    `story_approved` BOOLEAN NOT NULL DEFAULT false,
    `verified_amount` DECIMAL(10, 2) NULL,
    `collected_amount` DECIMAL(10, 2) NOT NULL DEFAULT 0,
    `released_amount` DECIMAL(10, 2) NOT NULL DEFAULT 0,
    `status` ENUM('DRAFT', 'PENDING_VERIFICATION', 'VERIFIED', 'PENDING', 'VERIFICATION_NEEDED', 'UPDATE_NEEDED', 'CANCELLED', 'LIVE_CAMPAIGN', 'HOSPITAL_CHANGE_REQUESTED', 'REVERIFYING', 'LIVE_UPDATED', 'COMPLETED', 'CLOSED', 'EXPIRED') NOT NULL DEFAULT 'DRAFT',
    `public_url` VARCHAR(191) NULL,
    `qr_code_url` VARCHAR(191) NULL,
    `upi_id` VARCHAR(191) NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updated_at` DATETIME(3) NOT NULL,
    `expires_at` DATETIME(3) NULL,

    UNIQUE INDEX `Campaign_public_url_key`(`public_url`),
    UNIQUE INDEX `Campaign_upi_id_key`(`upi_id`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `CampaignDocument` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `document_type` VARCHAR(191) NOT NULL,
    `file_url` VARCHAR(191) NOT NULL,
    `file_name` VARCHAR(191) NOT NULL,
    `uploaded_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `VerificationRecord` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `status` ENUM('VERIFIED', 'PENDING', 'VERIFICATION_NEEDED', 'UPDATE_NEEDED', 'CANCELLED') NOT NULL,
    `extracted_data` JSON NULL,
    `issues` JSON NULL,
    `tampered_docs` JSON NULL,
    `risk_score` INTEGER NOT NULL DEFAULT 0,
    `has_expired` BOOLEAN NOT NULL DEFAULT false,
    `has_tampering` BOOLEAN NOT NULL DEFAULT false,
    `admin_notes` VARCHAR(191) NULL,
    `verified_by` INTEGER NULL,
    `verified_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Donation` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `donor_name` VARCHAR(191) NOT NULL,
    `donor_email` VARCHAR(191) NOT NULL,
    `is_anonymous` BOOLEAN NOT NULL DEFAULT false,
    `amount` DECIMAL(10, 2) NOT NULL,
    `payment_id` VARCHAR(191) NULL,
    `order_id` VARCHAR(191) NULL,
    `status` ENUM('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED') NOT NULL DEFAULT 'PENDING',
    `receipt_sent` BOOLEAN NOT NULL DEFAULT false,
    `donated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `FundRelease` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `amount` DECIMAL(10, 2) NOT NULL,
    `hms_payment_id` VARCHAR(191) NULL,
    `hospital_confirmed` BOOLEAN NOT NULL DEFAULT false,
    `triggered_by` ENUM('MILESTONE', 'MANUAL', 'ADMIN') NOT NULL DEFAULT 'MILESTONE',
    `status` ENUM('PENDING', 'APPROVED', 'BLOCKED', 'COMPLETED') NOT NULL DEFAULT 'PENDING',
    `block_reason` VARCHAR(191) NULL,
    `released_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `CampaignUpdate` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `update_text` TEXT NOT NULL,
    `is_milestone` BOOLEAN NOT NULL DEFAULT false,
    `notify_donors` BOOLEAN NOT NULL DEFAULT false,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Suggestion` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `disease` VARCHAR(191) NOT NULL,
    `suggestion_text` TEXT NOT NULL,
    `hospital_name` VARCHAR(191) NULL,
    `hospital_address` VARCHAR(191) NULL,
    `google_places_verified` BOOLEAN NOT NULL DEFAULT false,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `NGO` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(191) NOT NULL,
    `email` VARCHAR(191) NOT NULL,
    `phone` VARCHAR(191) NULL,
    `city` VARCHAR(191) NULL,
    `state` VARCHAR(191) NULL,
    `specializations` JSON NULL,
    `is_verified` BOOLEAN NOT NULL DEFAULT true,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE INDEX `NGO_email_key`(`email`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `NGOMatch` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `ngo_id` INTEGER NOT NULL,
    `status` ENUM('NOTIFIED', 'ACCEPTED', 'REJECTED', 'PENDING') NOT NULL DEFAULT 'NOTIFIED',
    `notified_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `responded_at` DATETIME(3) NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `AdminAuditLog` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `admin_id` INTEGER NOT NULL,
    `action` VARCHAR(191) NOT NULL,
    `target_type` VARCHAR(191) NOT NULL,
    `target_id` INTEGER NOT NULL,
    `notes` TEXT NULL,
    `performed_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Blacklist` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `aadhaar_number` VARCHAR(191) NOT NULL,
    `phone` VARCHAR(191) NULL,
    `reason` VARCHAR(191) NOT NULL,
    `blacklisted_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `blacklisted_by` INTEGER NOT NULL,

    UNIQUE INDEX `Blacklist_aadhaar_number_key`(`aadhaar_number`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `OTP` ADD CONSTRAINT `OTP_user_id_fkey` FOREIGN KEY (`user_id`) REFERENCES `User`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Campaign` ADD CONSTRAINT `Campaign_patient_id_fkey` FOREIGN KEY (`patient_id`) REFERENCES `User`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Campaign` ADD CONSTRAINT `Campaign_hospital_id_fkey` FOREIGN KEY (`hospital_id`) REFERENCES `Hospital`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `CampaignDocument` ADD CONSTRAINT `CampaignDocument_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `VerificationRecord` ADD CONSTRAINT `VerificationRecord_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Donation` ADD CONSTRAINT `Donation_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `FundRelease` ADD CONSTRAINT `FundRelease_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `CampaignUpdate` ADD CONSTRAINT `CampaignUpdate_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `NGOMatch` ADD CONSTRAINT `NGOMatch_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `NGOMatch` ADD CONSTRAINT `NGOMatch_ngo_id_fkey` FOREIGN KEY (`ngo_id`) REFERENCES `NGO`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `AdminAuditLog` ADD CONSTRAINT `AdminAuditLog_admin_id_fkey` FOREIGN KEY (`admin_id`) REFERENCES `User`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
