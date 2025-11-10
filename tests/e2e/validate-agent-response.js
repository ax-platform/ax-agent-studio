#!/usr/bin/env node
/**
 * E2E Validation Helper: Validate Agent Response
 *
 * Reusable script to test agent responses using MCP JAM SDK.
 * Accepts command-line arguments for agent names.
 *
 * Usage:
 *   node validate-agent-response.js <target_agent> <sender_agent> [test_message]
 *
 * Example:
 *   node validate-agent-response.js ghost_ray_363 lunar_craft_128 "Hello!"
 *
 * Exit Codes:
 *   0 - Success (agent responded correctly)
 *   1 - Failure (no response or error)
 */

import { MCPClientManager } from '@mcpjam/sdk';

// Parse command-line arguments
const args = process.argv.slice(2);

if (args.length < 2) {
  console.error('Usage: node validate-agent-response.js <target_agent> <sender_agent> [test_message] [timeout]');
  console.error('Example: node validate-agent-response.js ghost_ray_363 lunar_craft_128 "Hello!" 10');
  process.exit(1);
}

const TARGET_AGENT = args[0];
const SENDER_AGENT = args[1];
const TEST_MESSAGE = args[2] || `E2E Test: Validation for ${TARGET_AGENT}`;
const TIMEOUT = parseInt(args[3]) || 180;

// MCP JAM SDK config
const mcpConfig = {
  [TARGET_AGENT]: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      `http://localhost:8002/mcp/agents/${TARGET_AGENT}`,
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

async function validateAgentResponse() {
  console.log('\n' + '='.repeat(80));
  console.log('E2E Agent Response Validation');
  console.log('='.repeat(80));
  console.log(`\nTarget Agent: ${TARGET_AGENT}`);
  console.log(`Sender Agent: ${SENDER_AGENT}`);
  console.log(`Test Message: "${TEST_MESSAGE}"`);
  console.log('='.repeat(80));

  try {
    // Connect to agents
    console.log(`\nConnecting to agents via MCP JAM SDK...`);
    const manager = new MCPClientManager(mcpConfig, {
      defaultClientName: 'E2E Test',
      defaultClientVersion: '1.0.0'
    });
    console.log('✓ Connected to agents');

    // Send test message with @mention and wait for response
    const messageWithMention = `@${TARGET_AGENT} ${TEST_MESSAGE}`;
    console.log(`\nSending test message FROM ${SENDER_AGENT} TO ${TARGET_AGENT}`);
    console.log(`  Using wait=true, wait_mode='mentions' (waits for response)`);

    const sendResult = await manager.executeTool(SENDER_AGENT, 'messages', {
      action: 'send',
      content: messageWithMention,
      wait: true,
      wait_mode: 'mentions',
      timeout: TIMEOUT
    });
    console.log('✓ Message sent and response received');

    const messages = sendResult.messages || [];
    console.log(`  Received ${messages.length} message(s)`);

    // Find response from target agent
    const agentResponse = messages.find(m => m.sender_name === TARGET_AGENT);

    if (agentResponse) {
      console.log('\n✅ SUCCESS: Agent responded!');
      console.log(`  Message ID: ${agentResponse.id.substring(0, 8)}`);
      console.log(`  From: ${agentResponse.sender_name}`);
      console.log(`  Content Preview: ${agentResponse.content.substring(0, 100)}...`);
      console.log('='.repeat(80) + '\n');
      return true;
    } else {
      console.log('\n❌ FAILURE: No response from ' + TARGET_AGENT);
      if (messages.length > 0) {
        console.log('Messages received from other agents:');
        messages.forEach(m => {
          console.log(`  - ${m.sender_name}: ${m.content.substring(0, 50)}...`);
        });
      }
      console.log('='.repeat(80) + '\n');
      return false;
    }

  } catch (error) {
    console.log('\n💥 ERROR during validation:');
    console.error(error.message);
    console.log('='.repeat(80) + '\n');
    return false;
  }
}

// Run validation
validateAgentResponse()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('\n💥 Uncaught error:', error);
    process.exit(1);
  });
