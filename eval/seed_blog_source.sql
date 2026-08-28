-- Seed blog_source
-- Run via pgAdmin or: docker exec -i <postgres_container> psql -U <user> -d <db> < eval/seed_blog_source.sql

INSERT INTO blog_source (id, source, rss_feed_link, created_at) VALUES
  (gen_random_uuid(), 'Cloudflare',          'https://blog.cloudflare.com/rss/',                  now()),
  (gen_random_uuid(), 'GitHub',              'https://github.blog/engineering/feed/',              now()),
  (gen_random_uuid(), 'Meta',                'https://engineering.fb.com/feed/',                   now()),
  (gen_random_uuid(), 'AWS',                 'https://aws.amazon.com/blogs/architecture/feed/',    now()),
  (gen_random_uuid(), 'Slack',               'https://slack.engineering/feed/',                    now()),
  (gen_random_uuid(), 'Netflix',             'https://netflixtechblog.medium.com/feed',            now()),
  (gen_random_uuid(), 'Airbnb',              'https://medium.com/feed/airbnb-engineering',         now()),
  (gen_random_uuid(), 'Dropbox',             'https://dropbox.tech/feed',                          now()),
  (gen_random_uuid(), 'Discord',             'https://discord.com/blog/rss.xml',                   now()),
  (gen_random_uuid(), 'Spotify',             'https://engineering.atspotify.com/feed/',            now()),
  (gen_random_uuid(), 'Stripe',              'https://stripe.com/blog/feed.rss',                   now()),
  (gen_random_uuid(), 'Microsoft',           'https://devblogs.microsoft.com/landing/',            now()),
  (gen_random_uuid(), 'Google Research',     'https://research.google/blog/rss/',                  now()),
  (gen_random_uuid(), 'All Things Distributed', 'https://www.allthingsdistributed.com/atom.xml',   now()),
  (gen_random_uuid(), 'Medium Engineering',   'https://medium.engineering/feed',                    now()),
  (gen_random_uuid(), 'ByteByteGo',           'https://blog.bytebytego.com/feed',                   now()),
  (gen_random_uuid(), 'Julia Evans',          'https://jvns.ca/atom.xml',                           now()),
  (gen_random_uuid(), 'Grab',                 'https://engineering.grab.com/feed.xml',              now()),
  (gen_random_uuid(), 'Pinterest',            'https://medium.com/feed/pinterest-engineering',      now())
ON CONFLICT DO NOTHING;

