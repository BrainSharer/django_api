-- updates for production May 2025
ALTER TABLE neuroglancer_state ADD COLUMN FK_prep_id VARCHAR(20) DEFAULT NULL AFTER FK_lab_id;
DROP TABLE neuroglancer_state_revision;
ALTER TABLE neuroglancer_state DROP COLUMN user_date;
