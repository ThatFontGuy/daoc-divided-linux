-- Lough Derg bounty camp: nine additional level-10 empyrean orbs around
-- the existing spawn at local /loc 61481,16258,5200 (Region 200).
-- Apply with the server stopped. Fixed Mob_ID values make this idempotent.
-- The existing monster and all other camps remain untouched.

BEGIN IMMEDIATE;

WITH additions(Mob_ID, X, Y, Z, Heading) AS (
    VALUES
    ('2a7ac6af-c772-5c68-b7fa-a9d5745401b8', 381901, 500258, 5200,  512),
    ('79f199d8-6047-5015-945a-67150f444be9', 381803, 500528, 5200, 1024),
    ('4f391ead-15fd-573f-82d4-eee33ff2df70', 381554, 500672, 5200, 1536),
    ('5446524f-04b5-57b6-a2ec-92255f59f707', 381271, 500622, 5200, 2048),
    ('c80736b4-e993-5138-b3e7-3c13c0160331', 381086, 500402, 5200, 2560),
    ('9078a393-c577-581f-be57-da6f52815f55', 381086, 500114, 5200, 3072),
    ('91c81746-117c-5ff6-9e2b-da9c4f6b7771', 381271, 499894, 5200, 3584),
    ('a343ea70-206d-5a3c-bb51-9b8b581f85fb', 381554, 499844, 5200,    0),
    ('1e5cdddd-55ae-57d0-9ee1-f182425d27b4', 381803, 499988, 5200,  256)
)
INSERT OR IGNORE INTO Mob (
    ClassType, TranslationId, Name, Suffix, Guild, ExamineArticle,
    MessageArticle, X, Y, Z, Speed, Heading, Region, Model, Size,
    Strength, Constitution, Dexterity, Quickness, Intelligence, Piety,
    Empathy, Charisma, Level, Realm, EquipmentTemplateID,
    ItemsListTemplateID, NPCTemplateID, Race, Flags, AggroLevel,
    AggroRange, MeleeDamageType, RespawnInterval, FactionID, BodyType,
    HouseNumber, Brain, PathID, OwnerID, RoamingRange, IsCloakHoodUp,
    Gender, PackageID, VisibleWeaponSlots, LastTimeRowUpdated, Mob_ID
)
SELECT
    seed.ClassType, seed.TranslationId, seed.Name, seed.Suffix, seed.Guild,
    seed.ExamineArticle, seed.MessageArticle, extra.X, extra.Y, extra.Z,
    seed.Speed, extra.Heading, seed.Region, seed.Model, seed.Size,
    seed.Strength, seed.Constitution, seed.Dexterity, seed.Quickness,
    seed.Intelligence, seed.Piety, seed.Empathy, seed.Charisma,
    seed.Level, seed.Realm, seed.EquipmentTemplateID,
    seed.ItemsListTemplateID, seed.NPCTemplateID, seed.Race, seed.Flags,
    seed.AggroLevel, seed.AggroRange, seed.MeleeDamageType,
    seed.RespawnInterval, seed.FactionID, seed.BodyType, seed.HouseNumber,
    seed.Brain, seed.PathID, seed.OwnerID, seed.RoamingRange,
    seed.IsCloakHoodUp, seed.Gender, seed.PackageID,
    seed.VisibleWeaponSlots, seed.LastTimeRowUpdated, extra.Mob_ID
FROM Mob AS seed
CROSS JOIN additions AS extra
WHERE seed.Mob_ID = '381ccf94-bb14-4c58-a24d-4d4e5f9f2ff9'
  AND seed.Region = 200
  AND seed.Name = 'empyrean orb'
  AND seed.Level = 10;

COMMIT;
