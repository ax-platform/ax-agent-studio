/**
 * E2E TEST 1: Validate Echo Monitor Deployment
 *
 * Test Flow:
 * 1. Deploy Ghost Ray 363 + Echo via dashboard (manual step - use E2E automation)
 * 2. Use MCP JAM SDK to send test message FROM lunar_craft_128 TO ghost_ray_363
 * 3. Verify Echo monitor echoes the message back to lunar_craft_128
 *
 * Prerequisites:
 * - Dashboard running at http://127.0.0.1:8000
 * - Backend API at localhost:8002
 * - Deploy Ghost Ray 363 + Echo via dashboard BEFORE running this test
 * - lunar_craft_128 must be available (doesn't need to be running, just configured)
 *
 * Why use two agents?
 * - System blocks self-mentions to prevent loops
 * - Must send FROM lunar_craft_128 TO ghost_ray_363 (not FROM ghost_ray_363)
 *
 * To deploy manually:
 * 1. Open http://127.0.0.1:8000
 * 2. Select "Ghost Ray 363" from Agent dropdown
 * 3. Select "Echo (Simple)" from Agent Type dropdown
 * 4. Click "Deploy Agent" button
 * 5. Wait for agent to appear in Running Agents section
 * 6. Run this test: npm run test:e2e:echo
 */

import { MCPClientManager } from '@mcpjam/sdk';

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const AGENT_NAME = 'ghost_ray_363';  // Agent with Echo monitor deployed
const SENDER_AGENT = 'lunar_craft_128';  // Agent to send test messages FROM

// MCP JAM SDK config for testing the deployed agents
const mcpConfig = {
  [AGENT_NAME]: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      `http://localhost:8002/mcp/agents/${AGENT_NAME}`,
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  [SENDER_AGENT]: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      `http://localhost:8002/mcp/agents/${SENDER_AGENT}`,
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

async function testAgentWithMCPJAM() {
  console.log('\n' + '='.repeat(80));
  console.log('Testing Agent with MCP JAM SDK');
  console.log('='.repeat(80));

  console.log(`\nConnecting to agents via MCP JAM SDK...`);
  const manager = new MCPClientManager(mcpConfig, {
    defaultClientName: 'E2E Test',
    defaultClientVersion: '1.0.0'
  });
  console.log('✓ Connected to agents');

  // Send test message FROM sender agent TO echo agent with wait=true
  const testMessage = 'E2E Test: Hello Echo Monitor!';
  const messageWithMention = `@${AGENT_NAME} ${testMessage}`;
  console.log(`\nSending test message FROM ${SENDER_AGENT} TO ${AGENT_NAME}:`);
  console.log(`  Message: "${messageWithMention}"`);
  console.log(`  Using wait=true, wait_mode='mentions' (waits for response)`);

  const sendResult = await manager.executeTool(SENDER_AGENT, 'messages', {
    action: 'send',
    content: messageWithMention,
    wait: true,
    wait_mode: 'mentions'
  });
  console.log('✓ Message sent and response received');

  const messages = sendResult.messages || [];
  console.log(`  Received ${messages.length} message(s)`);

  // Show ALL messages received with full details for debugging
  if (messages.length > 0) {
    console.log('\n📋 All messages received:');
    messages.forEach((m, idx) => {
      console.log(`\n  Message ${idx + 1}:`);
      console.log(`    ID: ${m.id}`);
      console.log(`    From: ${m.sender_name}`);
      console.log(`    Content: ${m.content}`);
      console.log(`    Created: ${m.created_at || 'N/A'}`);
    });
  }

  // Find the echo response - check if sender is AGENT_NAME
  const echoResponse = messages.find(m =>
    m.sender_name === AGENT_NAME
  );

  if (echoResponse) {
    console.log('\n✅ SUCCESS: Echo monitor responded!');
    console.log(`  Message ID: ${echoResponse.id.substring(0, 8)}`);
    console.log(`  From: ${echoResponse.sender_name}`);
    console.log(`  Content: ${echoResponse.content}`);

    // Check if content includes the test message
    if (echoResponse.content.includes(testMessage)) {
      console.log('\n✅ Content validation PASSED: Echo includes original message');
    } else {
      console.log('\n⚠️  Content validation WARNING: Echo may have modified the message');
    }
    return true;
  } else {
    console.log('\n❌ FAILURE: Did not receive echo response from ' + AGENT_NAME);
    return false;
  }
}

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('E2E TEST 1: Echo Monitor Validation');
  console.log('='.repeat(80));
  console.log('\nTest Objective:');
  console.log('  1. Verify Ghost Ray 363 + Echo is deployed (prerequisite)');
  console.log('  2. Send test message via MCP JAM SDK');
  console.log('  3. Verify echo response is received');
  console.log('\nPrerequisite: Deploy agent via dashboard first!');
  console.log('  - Agent: Ghost Ray 363');
  console.log('  - Type: Echo (Simple)');
  console.log('='.repeat(80));

  try {
    // Test via MCP JAM SDK
    const success = await testAgentWithMCPJAM();

    // Final result
    console.log('\n' + '='.repeat(80));
    if (success) {
      console.log('✅ E2E TEST 1 PASSED');
      console.log('='.repeat(80) + '\n');
      process.exit(0);
    } else {
      console.log('❌ E2E TEST 1 FAILED');
      console.log('='.repeat(80) + '\n');
      process.exit(1);
    }
  } catch (error) {
    console.log('\n' + '='.repeat(80));
    console.log('💥 E2E TEST 1 ERROR');
    console.log('='.repeat(80));
    console.error(error);
    process.exit(1);
  }
}

main();
