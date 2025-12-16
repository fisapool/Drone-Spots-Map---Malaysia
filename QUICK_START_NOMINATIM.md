# Quick Start: Self-Hosted Nominatim

Get your self-hosted Nominatim instance running in 3 steps!

## Step 1: Run Setup Script

```bash
./setup_nominatim.sh
```

This will:
- Check prerequisites
- Create `.env` file
- Start the Nominatim container
- Begin importing Malaysia data

## Step 2: Wait for Import (2-6 hours)

Monitor progress:
```bash
docker-compose -f docker-compose.nominatim.yml logs -f
```

You'll know it's done when you see:
```
[INFO] Import complete!
```

## Step 3: Enable in API

Edit `.env`:
```bash
USE_SELF_HOSTED_NOMINATIM=true
NOMINATIM_URL=localhost:8080
NOMINATIM_SCHEME=http
```

Restart your API and you're done!

## Test It

```bash
# Check status
curl http://localhost:8080/status

# Test search
curl "http://localhost:8080/search?q=Kuala+Lumpur&format=json"
```

## Need Help?

See `NOMINATIM_SETUP.md` for detailed documentation.

