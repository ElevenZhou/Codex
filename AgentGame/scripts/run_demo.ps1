param(
  [string]$BaseUrl = "http://127.0.0.1:8787",
  [int]$Seed = 1,
  [string]$A = "botA",
  [string]$B = "botB",
  [int]$TimeoutSec = 3
)

$ErrorActionPreference = "Stop"

function EnsureServerUp($baseUrl) {
  try {
    $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/health" -TimeoutSec $TimeoutSec
    if ($health.status -ne "ok") {
      throw "health_not_ok: $($health | ConvertTo-Json -Depth 5)"
    }
  } catch {
    Write-Host "Cannot reach AgentGame platform at $baseUrl" -ForegroundColor Red
    Write-Host ""
    Write-Host "Start the server in another terminal first:" -ForegroundColor Yellow
    Write-Host "  cd I:\\Dev\\Codex\\AgentGame\\platform"
    Write-Host "  .\\.venv\\Scripts\\python -m uvicorn app.main:app --reload --port 8787"
    Write-Host ""
    Write-Host "Then re-run:" -ForegroundColor Yellow
    Write-Host "  cd I:\\Dev\\Codex\\AgentGame"
    Write-Host "  .\\scripts\\run_demo.ps1"
    throw
  }
}

function PostJson($url, $body) {
  return Invoke-RestMethod -Method Post -Uri $url -TimeoutSec $TimeoutSec -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 20)
}

function GetJson($url) {
  return Invoke-RestMethod -Method Get -Uri $url -TimeoutSec $TimeoutSec
}

Write-Host "BaseUrl: $BaseUrl"
Write-Host "Seed: $Seed"

EnsureServerUp $BaseUrl

Write-Host "`n== Grid Arena demo ==" -ForegroundColor Cyan
$m1 = PostJson "$BaseUrl/v1/matches" @{ game_id="grid-arena"; seed=$Seed; players=@($A,$B); max_turns=40 }
$mid1 = $m1.match_id
Write-Host "match_id: $mid1"

# Deterministic small script: move towards each other then attack.
$script = @(
  @{ agent=$A; action=@{ type="move"; dir="E" }; chat="gl hf" },
  @{ agent=$B; action=@{ type="move"; dir="W" } },
  @{ agent=$A; action=@{ type="move"; dir="S" } },
  @{ agent=$B; action=@{ type="move"; dir="N" } },
  @{ agent=$A; action=@{ type="attack" } },
  @{ agent=$B; action=@{ type="attack" } }
)

foreach ($s in $script) {
  $body = @{ agent_id=$s.agent; action=$s.action }
  if ($s.chat) { $body.chat = $s.chat }
  $r = PostJson "$BaseUrl/v1/matches/$mid1/act" $body
  if (-not $r.ok) { throw "grid-arena act failed: $($r | ConvertTo-Json -Depth 10)" }
}

$replay1 = GetJson "$BaseUrl/v1/matches/$mid1/replay"
Write-Host "events: $($replay1.events.Count)"
Write-Host "viewer: $BaseUrl/viewer/?match=$mid1"
Write-Host "leaderboard: $BaseUrl/v1/leaderboards/grid-arena"


Write-Host "`n== Mini Auction demo ==" -ForegroundColor Cyan
$m2 = PostJson "$BaseUrl/v1/matches" @{ game_id="mini-auction"; seed=$Seed; players=@($A,$B); max_turns=200 }
$mid2 = $m2.match_id
Write-Host "match_id: $mid2"

for ($i = 0; $i -lt 5; $i++) {
  $oa = GetJson "$BaseUrl/v1/matches/$mid2/observation/$A"
  $ob = GetJson "$BaseUrl/v1/matches/$mid2/observation/$B"

  $va = [int]$oa.observation.me.private_value
  $vb = [int]$ob.observation.me.private_value
  $ca = [int]$oa.observation.me.credits
  $cb = [int]$ob.observation.me.credits

  $bidA = [Math]::Max(0, [Math]::Min($ca, $va))
  $bidB = [Math]::Max(0, [Math]::Min($cb, $vb))

  $rA = PostJson "$BaseUrl/v1/matches/$mid2/act" @{ agent_id=$A; action=@{ type="bid"; amount=$bidA }; chat="value=$va" }
  if (-not $rA.ok) { throw "mini-auction bid A failed: $($rA | ConvertTo-Json -Depth 10)" }

  $rB = PostJson "$BaseUrl/v1/matches/$mid2/act" @{ agent_id=$B; action=@{ type="bid"; amount=$bidB } }
  if (-not $rB.ok) { throw "mini-auction bid B failed: $($rB | ConvertTo-Json -Depth 10)" }
}

$replay2 = GetJson "$BaseUrl/v1/matches/$mid2/replay"
Write-Host "events: $($replay2.events.Count)"
Write-Host "viewer: $BaseUrl/viewer/?match=$mid2"
Write-Host "leaderboard: $BaseUrl/v1/leaderboards/mini-auction"

Write-Host "`nDone." -ForegroundColor Green
