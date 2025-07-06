ALTER TABLE neuroglancer_state ADD COLUMN FK_prep_id VARCHAR(20) DEFAULT NULL AFTER FK_lab_id;
ALTER TABLE neuroglancer_state DROP COLUMN user_date;
DROP TABLE neuroglancer_state_revision;
