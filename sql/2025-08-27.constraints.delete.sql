-- updates for 2025-08-27
-- elastix trans
ALTER TABLE elastix_transformation  DROP FOREIGN KEY  `FK__ET_FK_prep_id`;
ALTER TABLE elastix_transformation ADD CONSTRAINT `FK__ET_FK_prep_id` FOREIGN KEY (`FK_prep_id`)  REFERENCES animal(`prep_id`) ON DELETE CASCADE;
-- annotation session
ALTER TABLE annotation_session  DROP FOREIGN KEY  `FK__annotation_session_animal`;
ALTER TABLE annotation_session ADD CONSTRAINT `FK__annotation_session_animal` FOREIGN KEY (`FK_prep_id`)  REFERENCES animal(`prep_id`) ON DELETE CASCADE;
-- annotation session labels
ALTER TABLE annotation_session_labels  DROP FOREIGN KEY  `FK__annotationsession_id`;
ALTER TABLE annotation_session_labels ADD CONSTRAINT `FK__annotationsession_id` FOREIGN KEY (`annotationsession_id`)  REFERENCES annotation_session(`id`) ON DELETE CASCADE;
-- histology
ALTER TABLE histology  DROP FOREIGN KEY  `FK__histology_animal`;
ALTER TABLE histology ADD CONSTRAINT `FK__histology_animal` FOREIGN KEY (`FK_prep_id`)  REFERENCES animal(`prep_id`) ON DELETE CASCADE;
-- scan_run
ALTER TABLE scan_run  DROP FOREIGN KEY  `FK__scan_run_FK_prep_id`;
ALTER TABLE scan_run ADD CONSTRAINT `FK__scan_run_FK_prep_id` FOREIGN KEY (`FK_prep_id`)  REFERENCES animal(`prep_id`) ON DELETE CASCADE;
-- slide
ALTER TABLE slide  DROP FOREIGN KEY  `FK__slide_scan_run`;
ALTER TABLE slide ADD CONSTRAINT `FK__slide_scan_run` FOREIGN KEY (`FK_scan_run_id`)  REFERENCES scan_run(`id`) ON DELETE CASCADE;
