-- Reescribe URLs guardadas en PostgreSQL tras migrar ficheros a S3 y activar STORAGE_BACKEND=s3.
--
-- Antes:  {APP_BASE_URL o API}/uploads/{clave_relativa}
-- Después: {S3_PUBLIC_BASE_URL}/{S3_KEY_PREFIX opcional}{clave_relativa}
--          (misma clave que sube migrate_uploads_to_s3.py)
--
-- Pasos recomendados:
--   1. Copia de seguridad de la BD.
--   2. Edita old_prefix y new_prefix en el bloque DO más abajo.
--   3. Ejecuta solo los SELECT de "vista previa" y revisa columnas.
--   4. BEGIN;  →  ejecuta el DO  →  COMMIT;  (o ROLLBACK; si algo falla).
--
-- new_prefix debe ser la URL pública final terminada en /, por ejemplo:
--   https://xxxx.r2.cloudflare.com/mi-app/
-- si S3_PUBLIC_BASE_URL es https://xxxx.r2.cloudflare.com/mi-app y las claves en bucket
-- son relativas (audio/..., uuid.pdf). Si usas S3_KEY_PREFIX=prod, incluye "prod/" en la base
-- pública o concatena: https://cdn.ejemplo.com/prod/

-- Vista previa (ajusta old_prefix igual que en el DO):
-- SELECT id, profile_photo_url AS actual
-- FROM users
-- WHERE profile_photo_url IS NOT NULL AND profile_photo_url LIKE 'https://CAMBIA-AQUI/uploads/%';

-- SELECT id, photo_url AS actual FROM youths
-- WHERE photo_url IS NOT NULL AND photo_url LIKE 'https://CAMBIA-AQUI/uploads/%';

-- SELECT session_id, url AS actual FROM session_audios
-- WHERE url LIKE 'https://CAMBIA-AQUI/uploads/%';

-- SELECT id, type, url AS actual FROM support_material
-- WHERE url LIKE 'https://CAMBIA-AQUI/uploads/%';

DO $$
DECLARE
    old_prefix text := 'https://api.example.com/uploads/';
    new_prefix text := 'https://pub-xxxxx.r2.dev/mi-proyecto/';
    n int;
BEGIN
    IF position('/uploads/' IN old_prefix) = 0 THEN
        RAISE EXCEPTION 'old_prefix debe contener /uploads/ (URL antigua de ficheros locales).';
    END IF;
    IF right(new_prefix, 1) <> '/' THEN
        RAISE EXCEPTION 'new_prefix debe terminar en /.';
    END IF;

    UPDATE users
    SET profile_photo_url = new_prefix || substring(profile_photo_url FROM length(old_prefix) + 1)
    WHERE profile_photo_url IS NOT NULL AND profile_photo_url LIKE old_prefix || '%';
    GET DIAGNOSTICS n = ROW_COUNT;
    RAISE NOTICE 'users.profile_photo_url actualizadas: %', n;

    UPDATE youths
    SET photo_url = new_prefix || substring(photo_url FROM length(old_prefix) + 1)
    WHERE photo_url IS NOT NULL AND photo_url LIKE old_prefix || '%';
    GET DIAGNOSTICS n = ROW_COUNT;
    RAISE NOTICE 'youths.photo_url actualizadas: %', n;

    UPDATE session_audios
    SET url = new_prefix || substring(url FROM length(old_prefix) + 1)
    WHERE url LIKE old_prefix || '%';
    GET DIAGNOSTICS n = ROW_COUNT;
    RAISE NOTICE 'session_audios.url actualizadas: %', n;

    UPDATE support_material
    SET url = new_prefix || substring(url FROM length(old_prefix) + 1)
    WHERE url LIKE old_prefix || '%';
    GET DIAGNOSTICS n = ROW_COUNT;
    RAISE NOTICE 'support_material.url actualizadas (solo filas bajo old_prefix): %', n;
END $$;
