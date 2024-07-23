-- start adds, drops and alters
drop table if exists annotation_session_new;
drop table if exists annotation_session_labels;
CREATE TABLE annotation_session_labels (
  id int(11) NOT NULL AUTO_INCREMENT,
  annotationsession_id int(11) NOT NULL,
  annotationlabel_id int(11) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY UK__annotationsession_id_label_id (annotationsession_id,annotationlabel_id),
  KEY K__annotation_session_annotation_label_label_id (annotationlabel_id),
  CONSTRAINT FK__annotationsession_id FOREIGN KEY (annotationsession_id) REFERENCES annotation_session (id),
  CONSTRAINT FK__annotation_label_id FOREIGN KEY (annotationlabel_id) REFERENCES annotation_label (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO annotation_session_labels (annotationsession_id, annotationlabel_id)
SELECT AS2.id as annotationsession_id, AL.id as annotationlable_id
FROM annotation_session AS2 
INNER JOIN annotation_label AL on AS2.FK_label_id = AL.id
WHERE AS2.active = 1
ORDER BY AS2.id, AL.id;

ALTER TABLE annotation_session DROP COLUMN FK_label_id;
ALTER TABLE annotation_session DROP FOREIGN KEY `FK__annotation_session_brain_region`;
ALTER TABLE annotation_session DROP INDEX `K__annotation_session_FK_brain_region_id`;
ALTER TABLE annotation_session DROP COLUMN FK_brain_region_id;
DROP VIEW IF EXISTS v_search_sessions;
CREATE VIEW v_search_sessions AS
SELECT
	AS2.id AS id,
	CONCAT(AS2.FK_prep_id, ' ', GROUP_CONCAT(AL.label), ' ', AU.username) AS animal_abbreviation_username,
	AL.label_type AS label_type
FROM annotation_session AS2
INNER JOIN annotation_label AL 
INNER JOIN annotation_session_labels ASL ON (AS2.id = ASL.annotationsession_id AND AL.id = ASL.annotationlabel_id)
INNER JOIN auth_user AU ON AS2.FK_user_id = AU.id
WHERE AS2.active = 1
AND AU.is_active = 1
AND AL.active = 1
GROUP BY AS2.id;

ALTER TABLE annotation_label ADD CONSTRAINT `UK__label` UNIQUE (label);
INSERT INTO annotation_label (label, label_type)
SELECT DISTINCT source AS label, 'cell' AS label_type
FROM marked_cells mc
ORDER BY mc.source;

INSERT INTO annotation_session_labels (annotationsession_id, annotationlabel_id)
SELECT DISTINCT as2.id, al.id
FROM annotation_session as2 
INNER JOIN marked_cells mc ON as2.id = mc.FK_session_id
INNER JOIN annotation_label al ON mc.source = al.label
WHERE as2.active = 1
ORDER BY as2.id; 

-- ALTER TABLE annotation_session DROP COLUMN annotation_type;
-- ALTER TABLE annotation_session DROP COLUMN FK_state_id;
ALTER TABLE marked_cells DROP FOREIGN KEY `FK__marked_cells_annotation_session`;
ALTER TABLE structure_com DROP FOREIGN KEY `FK__structure_com_annotation_session`;
ALTER TABLE polygon_sequences DROP FOREIGN KEY `FK_polygon_sequences_annotation_session`;


-- finished adds, drops and alters
insert into annotation_label (label_type, label) values ('cell', 'Fiducial_test');

