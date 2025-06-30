PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            email TEXT,
            phone TEXT,
            address TEXT,
            date_created TEXT NOT NULL
        );
INSERT INTO customers VALUES('b884998c-7d1a-4e21-bf22-bbefc8cde476','james biggley','james@biggley.com','508 555 1212','23 meadow lane wayland','2025-06-29T08:42:58.880057');
INSERT INTO customers VALUES('5aaa2a96-54dc-4f64-aaaa-7a971d8ccd05','elana wiggley','elana@wiggley.com','408 434 1111','101 main street agawam ma','2025-06-29T08:53:16.256885');
CREATE TABLE plant_notes (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            plant_name TEXT NOT NULL,
            condition TEXT NOT NULL,
            recommended_treatment TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('healthy', 'unhealthy', 'treated')),
            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        );
INSERT INTO plant_notes VALUES('1d9c96f1-96af-432c-bebe-824707f67b3e','b884998c-7d1a-4e21-bf22-bbefc8cde476','james biggley','arborvite','turning brown, needles falling','correct acidic soil','unhealthy','2025-06-29T08:43:51.111738','2025-06-29T08:43:51.111738');
INSERT INTO plant_notes VALUES('abd83533-26d6-4727-9939-a4237df7e56f','b884998c-7d1a-4e21-bf22-bbefc8cde476','james biggley','hostas','nice greenery, will need pruning in the fall','none at this time','healthy','2025-06-29T08:44:39.453948','2025-06-29T08:44:39.453948');
INSERT INTO plant_notes VALUES('a325ea69-428c-456f-91e3-c70dcd946ae4','5aaa2a96-54dc-4f64-aaaa-7a971d8ccd05','elana wiggley','red maple','leaves dropping','likely due to drought conditions.  start weekly watering','unhealthy','2025-06-29T08:54:05.564853','2025-06-29T08:54:05.564853');
INSERT INTO plant_notes VALUES('5a91496c-74ed-4a14-8cf5-2c8cc51179c9','5aaa2a96-54dc-4f64-aaaa-7a971d8ccd05','elana wiggley','sycamore backyard','most leaves/branches are dead','trim all dead branches.  fertilize via stakes at the drip line.  clear area around trunk at ground level, expose root flair','unhealthy','2025-06-29T08:55:23.286574','2025-06-29T08:55:23.286574');
INSERT INTO plant_notes VALUES('9b6e7857-6640-454a-a57a-020f09e82d08','5aaa2a96-54dc-4f64-aaaa-7a971d8ccd05','elana wiggley','violet bed (side yard)','great condition. perfect amount of sun/shade','no changes to plant care needed. rechecked.','healthy','2025-06-29T12:34:45.132923','2025-06-29T12:41:36.531867');
INSERT INTO plant_notes VALUES('b7171f26-168b-4f19-a6fe-6df0fd7a5fa3','b884998c-7d1a-4e21-bf22-bbefc8cde476','james biggley','all trees','they look good for this time of year (mid-summer)','wait until fall, reinspect','healthy','2025-06-29T12:49:07.496068','2025-06-29T12:49:07.496068');
CREATE TABLE note_images (
            id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            date_uploaded TEXT NOT NULL,
            FOREIGN KEY (note_id) REFERENCES plant_notes (id) ON DELETE CASCADE
        );
INSERT INTO note_images VALUES('2ef5b374-86d0-4354-bf4e-98a14a253d54','9b6e7857-6640-454a-a57a-020f09e82d08','35bde426-1691-4fe2-8ff2-12f777542a16.jpg','violets-bed.jpg','uploads/5aaa2a96-54dc-4f64-aaaa-7a971d8ccd05/9b6e7857-6640-454a-a57a-020f09e82d08/35bde426-1691-4fe2-8ff2-12f777542a16.jpg',249880,'2025-06-29T12:34:45.132923');
INSERT INTO note_images VALUES('a8cf9687-787c-4069-b9e0-e67a1e46eb2f','b7171f26-168b-4f19-a6fe-6df0fd7a5fa3','70d661a7-24d7-4925-99b3-1912af7b484c.jpg','old-sycamore-tree.jpg','uploads/b884998c-7d1a-4e21-bf22-bbefc8cde476/b7171f26-168b-4f19-a6fe-6df0fd7a5fa3/70d661a7-24d7-4925-99b3-1912af7b484c.jpg',317286,'2025-06-29T12:49:07.496068');
INSERT INTO note_images VALUES('f0ef3b81-feab-4144-b226-aee389473efb','b7171f26-168b-4f19-a6fe-6df0fd7a5fa3','4d15e1b0-1d7f-4ad1-bc7f-58663790e124.jpg','red-maple-tree.jpg','uploads/b884998c-7d1a-4e21-bf22-bbefc8cde476/b7171f26-168b-4f19-a6fe-6df0fd7a5fa3/4d15e1b0-1d7f-4ad1-bc7f-58663790e124.jpg',162105,'2025-06-29T12:49:07.496068');
COMMIT;
