ALTER TABLE neuroglancer_state ADD COLUMN FK_lab_id int(11) NOT NULL AFTER neuroglancer_state;
ALTER TABLE neuroglancer_state ADD INDEX `K__FK_lab_id` (`FK_lab_id`);

update neuroglancer_state set FK_lab_id = 2;
update neuroglancer_state set FK_lab_id = 1 where id in (809, 810, 872, 889);
update neuroglancer_state set FK_lab_id = 7 where id in (893, 898, 890);

ALTER TABLE neuroglancer_state ADD CONSTRAINT `FK__neuroglancer_state_auth_lab` FOREIGN KEY (FK_lab_id) REFERENCES auth_lab(id);
