/**
 * Hybrid E2E Test Suite - Message Board Awareness
 *
 * Combines deterministic echo tests with real agent validation.
 * Posts test results to aX space for easy review.
 *
 * Test Types:
 * 1. Echo Tests (Deterministic) - Validate message delivery and queue mechanics
 * 2. Agent Tests (Real LLM) - Validate queue awareness and intelligent responses
 *
 * Usage:
 *   npm run test:hybrid
 *
 * Prerequisites:
 *   - Local Docker running (localhost:8002)
 *   - Agent configs exist for: orion_344, lunar_craft_128, rigelz_334
 */

import { MCPClientManager } from '@mcpjam/sdk';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Configuration
const TEST_SPACE = 'madtank-workspace'; // Jacob's Workspace
const MONITOR_INIT_TIME = 10000; // 10s for monitors to start
const AGENT_PROCESSING_TIME = 10000; // 10s for Claude agents to process and respond

// Sleep utility
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Track spawned processes for cleanup
const monitorProcesses = [];

// Test results tracker
const testResults = {
  echo: [],
  agent: [],
  startTime: new Date(),
  endTime: null
};

function startMonitor(agentName, isEcho = false) {
  console.log(`  Starting ${isEcho ? 'echo' : 'agent'} monitor for ${agentName}...`);

  const configPath = join(projectRoot, 'configs', 'agents', `${agentName}.json`);
  const monitorType = isEcho ? 'echo_monitor' : 'claude_agent_sdk_monitor';

  // Spawn monitor process
  const monitorProcess = spawn(
    'uv',
    [
      'run', 'python', '-m',
      `ax_agent_studio.monitors.${monitorType}`,
      agentName,
      '--config', configPath
    ],
    {
      cwd: projectRoot,
      stdio: ['ignore', 'pipe', 'pipe'] // Capture stdout/stderr
    }
  );

  monitorProcesses.push({ name: agentName, process: monitorProcess, type: isEcho ? 'echo' : 'agent' });

  // Log errors
  monitorProcess.stderr.on('data', (data) => {
    const msg = data.toString();
    if (msg.includes('ERROR') || msg.includes('Error')) {
      console.error(`  [${agentName}] ${msg}`);
    }
  });

  monitorProcess.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      console.log(`  [${agentName}] Monitor exited with code ${code}`);
    }
  });

  return monitorProcess;
}

function stopAllMonitors() {
  console.log('\n🛑 Stopping all monitors...');
  for (const { name, process } of monitorProcesses) {
    try {
      process.kill('SIGTERM');
      console.log(`  Stopped ${name}`);
    } catch (error) {
      console.log(`  ${name} already stopped`);
    }
  }
}

// Cleanup on exit
process.on('exit', stopAllMonitors);
process.on('SIGINT', () => {
  stopAllMonitors();
  process.exit(130);
});
process.on('SIGTERM', () => {
  stopAllMonitors();
  process.exit(143);
});

// Config for MCPJam SDK
const config = {
  'orion_344': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/orion_344',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  'lunar_craft_128': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/lunar_craft_128',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  'rigelz_334': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/rigelz_334',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

/**
 * DETERMINISTIC TESTS - Using Echo Monitor
 * These validate basic message flow and queue mechanics
 */

async function testEchoBasicFlow(manager) {
  console.log('\n' + '='.repeat(80));
  console.log('ECHO Test 1: Basic Message Flow');
  console.log('='.repeat(80));

  const sender = 'orion_344';
  const receiver = 'lunar_craft_128'; // Using echo monitor

  // Send a single message
  console.log(`\n[${new Date().toISOString()}] Sending message...`);
  await manager.executeTool(sender, 'messages', {
    action: 'send',
    content: `@${receiver} [ECHO TEST] Hello, this is a basic test message`
  });

  await sleep(2000);

  // Check receiver got it
  const response = await manager.executeTool(receiver, 'messages', {
    action: 'check',
    since: '15m',
    limit: 5
  });

  console.log('\n📥 Echo Response:');
  const allMessages = response.messages || [];
  const echoResponses = allMessages.filter(m =>
    m.sender_name === receiver &&
    m.content.includes('[ECHO]')
  );

  if (echoResponses.length > 0) {
    console.log(echoResponses[0].content);
    const hasQueueInfo = /Queue depth: \d+/.test(echoResponses[0].content);

    testResults.echo.push({
      name: 'Basic Message Flow',
      passed: hasQueueInfo,
      details: 'Message delivered and echo includes queue info'
    });

    return { passed: hasQueueInfo };
  } else {
    console.log('❌ No echo response received');
    testResults.echo.push({
      name: 'Basic Message Flow',
      passed: false,
      error: 'No echo response'
    });
    return { passed: false, error: 'No echo response' };
  }
}

async function testEchoQueueDepth(manager) {
  console.log('\n' + '='.repeat(80));
  console.log('ECHO Test 2: Queue Depth Reporting');
  console.log('='.repeat(80));

  const sender = 'orion_344';
  const receiver = 'lunar_craft_128';

  // Send 3 rapid messages
  console.log(`\n[${new Date().toISOString()}] Sending 3 rapid messages...`);
  for (let i = 1; i <= 3; i++) {
    await manager.executeTool(sender, 'messages', {
      action: 'send',
      content: `@${receiver} [ECHO TEST] Rapid message ${i}`
    });
    await sleep(200);
  }

  await sleep(3000);

  // Check queue depth
  const response = await manager.executeTool(receiver, 'messages', {
    action: 'check',
    since: '15m',
    limit: 10
  });

  console.log('\n📊 Queue Depth Validation:');
  const allMessages = response.messages || [];
  const echoResponses = allMessages.filter(m =>
    m.sender_name === receiver &&
    m.content.includes('[ECHO]')
  );

  if (echoResponses.length > 0) {
    const lastEcho = echoResponses[0].content;
    console.log(lastEcho);

    // Should show queue depth decreasing as messages are processed
    const depthMatch = lastEcho.match(/Queue depth: (\d+)/);
    const depth = depthMatch ? parseInt(depthMatch[1]) : -1;
    const passed = depth >= 0; // Just validate it reports a depth

    testResults.echo.push({
      name: 'Queue Depth Reporting',
      passed,
      details: `Queue depth: ${depth}`
    });

    return { passed, depth };
  } else {
    testResults.echo.push({
      name: 'Queue Depth Reporting',
      passed: false,
      error: 'No echo response'
    });
    return { passed: false };
  }
}

/**
 * REAL AGENT TESTS - Using Ollama Monitors
 * These validate intelligent queue awareness and responses
 */

async function testAgentQueueAwareness(manager) {
  console.log('\n' + '='.repeat(80));
  console.log('AGENT Test 1: Queue Awareness');
  console.log('='.repeat(80));

  const sender = 'orion_344';
  const receiver = 'rigelz_334'; // Real agent

  // Send initial message
  console.log(`\n[${new Date().toISOString()}] Sending initial message...`);
  await manager.executeTool(sender, 'messages', {
    action: 'send',
    content: `@${receiver} [AGENT TEST] Task #1 - please process this`
  });

  await sleep(2000);

  // Send rapid fire while processing
  console.log(`[${new Date().toISOString()}] Sending rapid fire messages...`);
  for (let i = 2; i <= 4; i++) {
    await manager.executeTool(sender, 'messages', {
      action: 'send',
      content: `@${receiver} [AGENT TEST] Task #${i}`
    });
    await sleep(300);
  }

  // Ask about queue
  console.log(`\n[${new Date().toISOString()}] Asking about queue...`);
  await manager.executeTool(sender, 'messages', {
    action: 'send',
    content: `@${receiver} [AGENT TEST] How many messages do you see in your queue?`
  });

  console.log('⏱  Waiting for agent to process...');
  await sleep(AGENT_PROCESSING_TIME);

  // Validate response
  const response = await manager.executeTool(receiver, 'messages', {
    action: 'check',
    since: '15m',
    limit: 5
  });

  console.log('\n🤖 Agent Response:');
  const allMessages = response.messages || [];
  const agentResponses = allMessages.filter(m =>
    m.sender_name === receiver &&
    !m.content.includes('[AGENT TEST]')
  );

  if (agentResponses.length === 0) {
    console.log('❌ Agent did not respond');
    testResults.agent.push({
      name: 'Queue Awareness',
      passed: false,
      error: 'Agent did not respond'
    });
    return { passed: false };
  }

  const responseText = agentResponses[0].content.toLowerCase();
  const mentionsQueue = /queue|message|backlog/i.test(responseText);
  const mentionsNumber = /[2-5]/.test(responseText);

  console.log(`  Response: "${agentResponses[0].content.substring(0, 100)}..."`);
  console.log(`  ${mentionsQueue ? '✓' : '✗'} Mentions queue/messages`);
  console.log(`  ${mentionsNumber ? '✓' : '✗'} Mentions message count`);

  const passed = mentionsQueue && mentionsNumber;

  testResults.agent.push({
    name: 'Queue Awareness',
    passed,
    response: agentResponses[0].content.substring(0, 200)
  });

  return { passed };
}

async function testAgentMultipleSenders(manager) {
  console.log('\n' + '='.repeat(80));
  console.log('AGENT Test 2: Multiple Sender Identification');
  console.log('='.repeat(80));

  const sender1 = 'orion_344';
  const sender2 = 'lunar_craft_128';
  const receiver = 'rigelz_334';

  // Sender 1
  console.log(`\n[${new Date().toISOString()}] Sender 1 messaging...`);
  await manager.executeTool(sender1, 'messages', {
    action: 'send',
    content: `@${receiver} [AGENT TEST] Message from ${sender1}`
  });

  await sleep(1000);

  // Sender 2
  console.log(`[${new Date().toISOString()}] Sender 2 messaging...`);
  await manager.executeTool(sender2, 'messages', {
    action: 'send',
    content: `@${receiver} [AGENT TEST] Message from ${sender2}`
  });

  await sleep(1000);

  // Ask about senders
  console.log(`\n[${new Date().toISOString()}] Asking about senders...`);
  await manager.executeTool(sender1, 'messages', {
    action: 'send',
    content: `@${receiver} [AGENT TEST] Who has messaged you recently?`
  });

  console.log('⏱  Waiting for agent to process...');
  await sleep(AGENT_PROCESSING_TIME);

  // Validate response
  const response = await manager.executeTool(receiver, 'messages', {
    action: 'check',
    since: '15m',
    limit: 5
  });

  console.log('\n🤖 Agent Response:');
  const allMessages = response.messages || [];
  const agentResponses = allMessages.filter(m =>
    m.sender_name === receiver &&
    !m.content.includes('[AGENT TEST]')
  );

  if (agentResponses.length === 0) {
    console.log('❌ Agent did not respond');
    testResults.agent.push({
      name: 'Multiple Sender Identification',
      passed: false,
      error: 'Agent did not respond'
    });
    return { passed: false };
  }

  const responseText = agentResponses[0].content.toLowerCase();
  const identifiesSender1 = /orion/.test(responseText);
  const identifiesSender2 = /lunar/.test(responseText);

  console.log(`  Response: "${agentResponses[0].content.substring(0, 100)}..."`);
  console.log(`  ${identifiesSender1 ? '✓' : '✗'} Identifies sender 1 (orion_344)`);
  console.log(`  ${identifiesSender2 ? '✓' : '✗'} Identifies sender 2 (lunar_craft_128)`);

  const passed = identifiesSender1 && identifiesSender2;

  testResults.agent.push({
    name: 'Multiple Sender Identification',
    passed,
    response: agentResponses[0].content.substring(0, 200)
  });

  return { passed };
}

/**
 * Post test results to aX for review
 */
async function postTestResultsToAx(manager) {
  console.log('\n📤 Posting test results to aX...');

  testResults.endTime = new Date();
  const duration = Math.round((testResults.endTime - testResults.startTime) / 1000);

  const echoPassCount = testResults.echo.filter(t => t.passed).length;
  const agentPassCount = testResults.agent.filter(t => t.passed).length;
  const totalPass = echoPassCount + agentPassCount;
  const totalTests = testResults.echo.length + testResults.agent.length;

  const summary = `
## 🧪 E2E Test Results - Message Board Awareness

**Duration:** ${duration}s
**Passed:** ${totalPass}/${totalTests}
**Status:** ${totalPass === totalTests ? '✅ ALL PASSED' : '⚠️ SOME FAILED'}

### Echo Tests (Deterministic) - ${echoPassCount}/${testResults.echo.length}
${testResults.echo.map(t => `- ${t.passed ? '✅' : '❌'} ${t.name}${t.error ? ` - ${t.error}` : ''}`).join('\n')}

### Agent Tests (Real LLM) - ${agentPassCount}/${testResults.agent.length}
${testResults.agent.map(t => `- ${t.passed ? '✅' : '❌'} ${t.name}${t.error ? ` - ${t.error}` : ''}`).join('\n')}

---
*Automated test run at ${testResults.startTime.toISOString()}*
*Test agents: orion_344, lunar_craft_128, rigelz_334*
`.trim();

  try {
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: summary
    });
    console.log('✓ Test results posted to aX');
  } catch (error) {
    console.log('⚠️  Failed to post results to aX:', error.message);
  }
}

async function main() {
  console.log('='.repeat(80));
  console.log('Hybrid E2E Test Suite: Message Board Awareness');
  console.log('Testing in: Jacob\'s Workspace (madtank-workspace)');
  console.log('='.repeat(80));

  // Step 1: Start monitors
  console.log('\n🚀 Starting monitors...');
  console.log('Echo monitors (deterministic):');
  startMonitor('lunar_craft_128', true); // Echo for deterministic tests

  console.log('\nAgent monitors (real LLM):');
  startMonitor('rigelz_334', false); // Real agent for awareness tests
  startMonitor('orion_344', false); // Real agent for sending

  // Wait for monitors to initialize
  console.log(`\n⏱  Waiting ${MONITOR_INIT_TIME/1000}s for monitors to initialize...`);
  await sleep(MONITOR_INIT_TIME);
  console.log('✓ Monitors should be ready\n');

  // Initialize MCPClientManager
  const manager = new MCPClientManager(config, {
    defaultClientName: 'Hybrid E2E Test',
    defaultClientVersion: '1.0.0'
  });

  console.log('📡 MCP Manager initialized\n');

  // Run Echo Tests
  console.log('\n' + '='.repeat(80));
  console.log('PHASE 1: DETERMINISTIC ECHO TESTS');
  console.log('='.repeat(80));

  try {
    await testEchoBasicFlow(manager);
  } catch (error) {
    console.error(`\n✗ Echo basic flow failed: ${error.message}`);
    testResults.echo.push({ name: 'Basic Message Flow', passed: false, error: error.message });
  }

  try {
    await testEchoQueueDepth(manager);
  } catch (error) {
    console.error(`\n✗ Echo queue depth failed: ${error.message}`);
    testResults.echo.push({ name: 'Queue Depth Reporting', passed: false, error: error.message });
  }

  // Run Agent Tests
  console.log('\n' + '='.repeat(80));
  console.log('PHASE 2: REAL AGENT TESTS');
  console.log('='.repeat(80));

  try {
    await testAgentQueueAwareness(manager);
  } catch (error) {
    console.error(`\n✗ Agent queue awareness failed: ${error.message}`);
    testResults.agent.push({ name: 'Queue Awareness', passed: false, error: error.message });
  }

  try {
    await testAgentMultipleSenders(manager);
  } catch (error) {
    console.error(`\n✗ Agent multiple senders failed: ${error.message}`);
    testResults.agent.push({ name: 'Multiple Sender Identification', passed: false, error: error.message });
  }

  // Post results to aX
  await postTestResultsToAx(manager);

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('Test Results Summary');
  console.log('='.repeat(80));

  const echoPassCount = testResults.echo.filter(t => t.passed).length;
  const agentPassCount = testResults.agent.filter(t => t.passed).length;
  const totalPass = echoPassCount + agentPassCount;
  const totalTests = testResults.echo.length + testResults.agent.length;

  console.log(`\nEcho Tests: ${echoPassCount}/${testResults.echo.length}`);
  testResults.echo.forEach(t => {
    console.log(`  ${t.passed ? '✓' : '✗'} ${t.name}`);
    if (t.error) console.log(`    Error: ${t.error}`);
  });

  console.log(`\nAgent Tests: ${agentPassCount}/${testResults.agent.length}`);
  testResults.agent.forEach(t => {
    console.log(`  ${t.passed ? '✓' : '✗'} ${t.name}`);
    if (t.error) console.log(`    Error: ${t.error}`);
  });

  console.log(`\nTotal: ${totalPass}/${totalTests} passed`);

  // Disconnect all servers
  try {
    await manager.disconnectServer('orion_344');
    await manager.disconnectServer('lunar_craft_128');
    await manager.disconnectServer('rigelz_334');
  } catch (error) {
    // Ignore disconnect errors
  }

  // Stop monitors
  stopAllMonitors();

  // Wait for cleanup
  await sleep(2000);

  const exitCode = totalPass === totalTests ? 0 : 1;
  if (exitCode === 0) {
    console.log('\n✅ All tests passed!');
    console.log('📊 View detailed results in aX (Jacob\'s Workspace)');
  } else {
    console.log('\n❌ Some tests failed - see errors above');
    console.log('📊 View detailed results in aX (Jacob\'s Workspace)');
  }

  process.exit(exitCode);
}

main().catch((error) => {
  console.error('\n✗ Fatal error:', error);
  stopAllMonitors();
  process.exit(1);
});
