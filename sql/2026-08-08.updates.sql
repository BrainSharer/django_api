select count(*)
from elastix_transformation where FK_prep_id = 'DK293_TG';


SELECT DISTINCT TABLE_NAME 
FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME = 'FK_prep_id'
  AND TABLE_SCHEMA = 'brainsharer' order by TABLE_NAME; 

show create table neuroglancer_state;

-- drop and re add keys
-- annotation_session
ALTER TABLE annotation_session DROP FOREIGN KEY FK__annotation_session_animal;
ALTER TABLE annotation_session ADD CONSTRAINT FK__annotation_session_animal
FOREIGN KEY (FK_prep_id) REFERENCES animal(prep_id) ON UPDATE CASCADE ON DELETE CASCADE;
-- elastix_transformation
ALTER TABLE elastix_transformation DROP FOREIGN KEY FK__ET_FK_prep_id;
ALTER TABLE elastix_transformation ADD CONSTRAINT FK__ET_FK_prep_id
FOREIGN KEY (FK_prep_id) REFERENCES animal(prep_id) ON UPDATE CASCADE ON DELETE CASCADE;
-- histology
ALTER TABLE histology DROP FOREIGN KEY FK__histology_animal;
ALTER TABLE histology ADD CONSTRAINT FK__histology_animal
FOREIGN KEY (FK_prep_id) REFERENCES animal(prep_id) ON UPDATE CASCADE ON DELETE CASCADE;
-- injection
ALTER TABLE injection DROP FOREIGN KEY FK__injection_animal;
ALTER TABLE injection ADD CONSTRAINT FK__injection_animal
FOREIGN KEY (FK_prep_id) REFERENCES animal(prep_id) ON UPDATE CASCADE ON DELETE CASCADE;
-- scan_run
ALTER TABLE scan_run DROP FOREIGN KEY FK__scan_run_FK_prep_id;
ALTER TABLE scan_run ADD CONSTRAINT FK__scan_run_FK_prep_id
FOREIGN KEY (FK_prep_id) REFERENCES animal(prep_id) ON UPDATE CASCADE ON DELETE CASCADE;
-- updates
-- neuroglancer_state
UPDATE animal SET prep_id = 'DK293_TG_V0' WHERE prep_id = 'DK293_TG';
UPDATE neuroglancer_state SET prep_id = 'DK293_TG_V0' WHERE prep_id = 'DK293_TG';





