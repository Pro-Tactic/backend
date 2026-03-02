from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0019_alter_desempenho_unique_together_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE
                _constraint_name text;
            BEGIN
                -- Remove qualquer FK existente que use backend_user.clube_id
                FOR _constraint_name IN
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                    JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
                    WHERE con.contype = 'f'
                      AND nsp.nspname = 'public'
                      AND rel.relname = 'backend_user'
                      AND att.attname = 'clube_id'
                LOOP
                    EXECUTE format('ALTER TABLE public.backend_user DROP CONSTRAINT IF EXISTS %I', _constraint_name);
                END LOOP;

                -- Converte o tipo para varchar(50) para aceitar IDs do padrão clb_xxx
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'backend_user'
                      AND column_name = 'clube_id'
                      AND data_type <> 'character varying'
                ) THEN
                    ALTER TABLE public.backend_user
                        ALTER COLUMN clube_id TYPE varchar(50)
                        USING clube_id::varchar(50);
                END IF;

                -- Limpa vínculos órfãos para permitir recriar FK
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'clube'
                ) THEN
                    UPDATE public.backend_user u
                    SET clube_id = NULL
                    WHERE u.clube_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM public.clube c
                          WHERE c.id_clube = u.clube_id
                      );
                END IF;

                -- Recria FK para a tabela correta (clube.id_clube)
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'backend_user_clube_id_fkey'
                ) THEN
                    ALTER TABLE public.backend_user
                        ADD CONSTRAINT backend_user_clube_id_fkey
                        FOREIGN KEY (clube_id)
                        REFERENCES public.clube (id_clube)
                        ON DELETE SET NULL;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                ALTER TABLE public.backend_user
                    DROP CONSTRAINT IF EXISTS backend_user_clube_id_fkey;
            END $$;
            """,
        ),
    ]
