-- Seed blog_source and allowed_users
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
  (gen_random_uuid(), 'Fly.io',              'https://fly.io/changelog.xml',                       now()),
  (gen_random_uuid(), 'Discord',             'https://discord.com/blog/rss.xml',                   now()),
  (gen_random_uuid(), 'Spotify',             'https://engineering.atspotify.com/feed/',            now()),
  (gen_random_uuid(), 'Google',              'https://feeds.feedburner.com/GDBcode',               now()),
  (gen_random_uuid(), 'Stripe',              'https://stripe.com/blog/feed.rss',                   now())
ON CONFLICT DO NOTHING;

-- Replace with your email
INSERT INTO allowed_users (id, email) VALUES
  (gen_random_uuid(), 'mridubhatnagar4@gmail.com')
ON CONFLICT DO NOTHING;
