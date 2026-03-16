param(
  [string]$BaseUrl = "http://127.0.0.1:8787",
  [int]$Seed = 1,
  [string]$A = "botA",
  [string]$B = "botB",
  [int]$TimeoutSec = 3,
  [ValidateSet("queue","direct")]
  [string]$MatchMode = "queue",
  [int]$QueueWaitSec = 15
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

function QueueJoin($gameId, $agentId, $rulesetVersion, $maxTurns) {
  return PostJson "$BaseUrl/v1/queue/join" @{ game_id=$gameId; agent_id=$agentId; ruleset_version=$rulesetVersion; max_turns=$maxTurns }
}

function WaitForMatch($ticketId) {
  $deadline = (Get-Date).AddSeconds($QueueWaitSec)
  while ((Get-Date) -lt $deadline) {
    $t = GetJson "$BaseUrl/v1/queue/status/$ticketId"
    if ($t.status -eq "matched" -and $t.match_id) { return $t.match_id }
    Start-Sleep -Milliseconds 350
  }
  throw "queue_timeout: ticket_id=$ticketId wait=$QueueWaitSec sec"
}

function CreateMatch($gameId, $rulesetVersion, $seed, $players, $maxTurns) {
  return PostJson "$BaseUrl/v1/matches" @{ game_id=$gameId; ruleset_version=$rulesetVersion; seed=$seed; players=$players; max_turns=$maxTurns }
}

function GetOrCreateMatchId($gameId, $rulesetVersion, $seed, $players, $maxTurns) {
  if ($MatchMode -eq "direct") {
    $m = CreateMatch $gameId $rulesetVersion $seed $players $maxTurns
    return $m.match_id
  }

  $t1 = QueueJoin $gameId $players[0] $rulesetVersion $maxTurns
  $t2 = QueueJoin $gameId $players[1] $rulesetVersion $maxTurns

  if ($t1.status -eq "matched" -and $t1.match_id) { return $t1.match_id }
  if ($t2.status -eq "matched" -and $t2.match_id) { return $t2.match_id }

  if ($t2.ticket_id) { return (WaitForMatch $t2.ticket_id) }
  if ($t1.ticket_id) { return (WaitForMatch $t1.ticket_id) }
  throw "queue_join_failed"
}

Write-Host "BaseUrl: $BaseUrl"
Write-Host "Seed: $Seed"

EnsureServerUp $BaseUrl

Write-Host "`n== Grid Arena demo ==" -ForegroundColor Cyan
$ruleset = "2026-03-15"
$mid1 = GetOrCreateMatchId "grid-arena" $ruleset $Seed @($A,$B) 40
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
$mid2 = GetOrCreateMatchId "mini-auction" $ruleset $Seed @($A,$B) 200
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
