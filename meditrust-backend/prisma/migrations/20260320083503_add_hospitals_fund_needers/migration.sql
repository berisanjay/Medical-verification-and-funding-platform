-- AlterTable
ALTER TABLE `campaigndocument` MODIFY `file_url` LONGTEXT NOT NULL;

-- CreateTable
CREATE TABLE `AccessibleHospital` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(191) NOT NULL,
    `name_aliases` JSON NULL,
    `city` VARCHAR(191) NOT NULL,
    `state` VARCHAR(191) NOT NULL,
    `pincode` VARCHAR(191) NOT NULL,
    `address` VARCHAR(191) NULL,
    `phone` VARCHAR(191) NULL,
    `email` VARCHAR(191) NULL,
    `is_hms_connected` BOOLEAN NOT NULL DEFAULT false,
    `hms_api_url` VARCHAR(191) NULL,
    `hms_api_key` VARCHAR(191) NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updated_at` DATETIME(3) NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `FundNeeder` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `campaign_id` INTEGER NOT NULL,
    `accessible_hospital_id` INTEGER NULL,
    `patient_name` VARCHAR(191) NOT NULL,
    `patient_aadhaar` VARCHAR(191) NOT NULL,
    `patient_age` INTEGER NULL,
    `patient_gender` VARCHAR(191) NULL,
    `disease` VARCHAR(191) NULL,
    `admission_date` VARCHAR(191) NULL,
    `hospital_name` VARCHAR(191) NOT NULL,
    `hospital_pincode` VARCHAR(191) NULL,
    `total_estimate` DECIMAL(10, 2) NOT NULL,
    `amount_paid` DECIMAL(10, 2) NOT NULL DEFAULT 0,
    `outstanding` DECIMAL(10, 2) NOT NULL,
    `source` ENUM('HMS_API', 'DOC_EXTRACTED') NOT NULL DEFAULT 'DOC_EXTRACTED',
    `hms_patient_id` INTEGER NULL,
    `admin_verified` BOOLEAN NOT NULL DEFAULT false,
    `admin_notes` TEXT NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updated_at` DATETIME(3) NOT NULL,

    UNIQUE INDEX `FundNeeder_campaign_id_key`(`campaign_id`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `FundNeeder` ADD CONSTRAINT `FundNeeder_campaign_id_fkey` FOREIGN KEY (`campaign_id`) REFERENCES `Campaign`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `FundNeeder` ADD CONSTRAINT `FundNeeder_accessible_hospital_id_fkey` FOREIGN KEY (`accessible_hospital_id`) REFERENCES `AccessibleHospital`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
