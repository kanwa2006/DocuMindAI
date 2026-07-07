const { createCanvas } = require('canvas')
const fs = require('fs')
const path = require('path')

const WIDTH = 1200
const HEIGHT = 630

const canvas = createCanvas(WIDTH, HEIGHT)
const ctx = canvas.getContext('2d')

// Brand blue background
ctx.fillStyle = '#1E40AF'
ctx.fillRect(0, 0, WIDTH, HEIGHT)

// Subtle gradient overlay
const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT)
gradient.addColorStop(0, 'rgba(30, 58, 175, 0.9)')
gradient.addColorStop(1, 'rgba(15, 30, 100, 0.95)')
ctx.fillStyle = gradient
ctx.fillRect(0, 0, WIDTH, HEIGHT)

// Title
ctx.fillStyle = '#FFFFFF'
ctx.font = 'bold 88px sans-serif'
ctx.textAlign = 'center'
ctx.textBaseline = 'middle'
ctx.fillText('DocuMindAI', WIDTH / 2, HEIGHT / 2 - 50)

// Subtitle
ctx.font = '36px sans-serif'
ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'
ctx.fillText('Document Intelligence for Indian Professionals', WIDTH / 2, HEIGHT / 2 + 50)

// Save output
const outputPath = path.join(__dirname, '../public/og-image.png')
fs.mkdirSync(path.dirname(outputPath), { recursive: true })
const buffer = canvas.toBuffer('image/png')
fs.writeFileSync(outputPath, buffer)
console.log('OG image generated:', outputPath)
