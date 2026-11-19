# FramePilot + n8n publishing

FramePilot sends a clip to n8n only after you choose **Approve & publish** or approve a scheduled post. New clips never publish automatically. Configure a Production webhook URL in **Settings → Connected apps → n8n publishing**. Add a bearer token there if your n8n webhook checks one.

## Workflow contract

Create a **Webhook** trigger using `POST` and the Production URL. FramePilot sends a `multipart/form-data` request with a JSON string in the `payload` field and the approved clip file in the `video` binary field. Parse `payload` as JSON; it has this shape:

```json
{
  "event": "framepilot.clip.approved",
  "postId": "stable-id-for-retries",
  "platform": "youtube | instagram | tiktok",
  "accountId": "FramePilot account id",
  "accountName": "connected account name",
  "title": "clip title",
  "caption": "post description and tags",
  "hashtags": ["Shorts"],
  "approvedAt": 0,
  "privacy": "public | unlisted | private"
}
```

Use `postId` as an idempotency key in the workflow so a retry does not create a duplicate post. Route by `platform` and upload the incoming `video` binary with credentials configured in n8n. Platform API access, review, account type, and publishing limits are controlled by each social network. The connected account IDs are labels for routing; n8n needs its own authorized credentials for each destination. Larger clips may exceed n8n's default webhook body limit; raise `N8N_PAYLOAD_SIZE_MAX` on your n8n instance if needed.

For a synchronous workflow, finish the upload before responding to the webhook. Return JSON such as:

```json
{"status":"posted","url":"https://…","remote_id":"…"}
```

FramePilot records the post as published from this response. If the workflow cannot publish, return a non-2xx response or `{"status":"failed","error":"…"}` so FramePilot records the failure and offers an explicit retry. A successful 2xx response without `status: posted` is recorded as **Sent to n8n**; it means n8n accepted the request, not that the social platform confirmed publication.

## Reliability and safety

- Keep the workflow URL private and use HTTPS. The optional bearer token is stored with the user's local settings and sent in the `Authorization` header.
- FramePilot streams the approved video directly to n8n after approval; it does not expose a local desktop file or require a public URL.
- FramePilot provides an `Idempotency-Key` header and `postId` in the body. Use these to avoid duplicate uploads if a network timeout causes a retry.
- n8n requests have a three-minute timeout. Network and workflow failures are retried after ten minutes, for three attempts total, with the same post ID; after that, the queue shows a failure and offers a manual retry.
- The app can pause all scheduled publishing. Clips waiting for approval do not publish until you approve them.
- Keep workflow execution logs and configure n8n's own retries and failure alerts for the platform nodes.
