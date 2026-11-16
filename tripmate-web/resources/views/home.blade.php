<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">

    <title>TripMate AI | Thoughtful Journeys</title>
    <link rel="icon" type="image/svg+xml" href="{{ asset('favicon.svg') }}">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">

    <style>
        :root {
            --cream: #f5f1e5;
            --paper: #faf8f0;
            --olive: #66794a;
            --olive-dark: #344b32;
            --forest: #1d382d;
            --sage: #dce4c8;
            --gold: #d4bd72;
            --ink: #273a30;
            --muted: #697469;
            --white: #fffef8;
            --line: rgba(52, 75, 50, .15);
            --shadow: 0 22px 65px rgba(51, 65, 44, .15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html {
            scroll-behavior: smooth;
            scroll-padding-top: 90px;
        }

        body {
            font-family: 'DM Sans', sans-serif;
            background: var(--cream);
            color: var(--ink);
            overflow-x: hidden;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        button, input, select {
            font: inherit;
        }

        button {
            cursor: pointer;
        }

        img {
            display: block;
            max-width: 100%;
        }

        .container {
            width: min(1240px, calc(100% - 64px));
            margin-inline: auto;
        }

        .serif {
            font-family: 'Playfair Display', Georgia, serif;
        }

        /* NAVIGATION */

        .navbar {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            z-index: 20;
            padding: 23px 0;
            color: white;
        }

        .nav-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }

        .logo {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -.7px;
            white-space: nowrap;
        }

        .logo-mark {
            width: 36px;
            height: 36px;
            display: grid;
            place-items: center;
            color: var(--forest);
            background: #e3efb7;
            border-radius: 50% 50% 45% 15%;
            transform: rotate(-12deg);
            font-size: 22px;
        }

        .logo-mark span {
            transform: rotate(12deg);
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 34px;
            font-size: 12px;
        }

        .nav-links a:not(.nav-button) {
            color: rgba(255,255,255,.88);
            transition: color .2s;
        }

        .nav-links a:hover {
            color: #d9ef9a;
        }

        .nav-button {
            padding: 12px 19px;
            border-radius: 50px;
            background: var(--forest);
            color: white;
            transition: .25s;
        }

        .nav-button:hover {
            background: #4c6840;
            transform: translateY(-2px);
        }

        /* HERO */

        .hero {
            position: relative;
            min-height: 730px;
            padding: 145px 0 100px;
            overflow: hidden;
            color: white;
            background: #8da59b;
            isolation: isolate;
        }

        .hero-bg {
            position: absolute;
            z-index: -3;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 48%;
            animation: sceneryReveal 1.3s ease both;
        }

        .hero::before {
            content: "";
            position: absolute;
            z-index: -2;
            inset: 0;
            background:
                linear-gradient(90deg,
                    rgba(15, 49, 43, .82) 0%,
                    rgba(24, 57, 49, .59) 37%,
                    rgba(36, 59, 47, .12) 74%,
                    rgba(35, 53, 39, .12) 100%),
                linear-gradient(0deg,
                    rgba(27, 54, 40, .46),
                    transparent 45%,
                    rgba(30, 48, 41, .15));
        }

        .hero::after {
            content: "";
            position: absolute;
            z-index: -1;
            bottom: -100px;
            left: -10%;
            width: 120%;
            height: 170px;
            background: var(--cream);
            border-radius: 50% 50% 0 0;
        }

        .hero-content {
            position: relative;
            z-index: 5;
            width: 52%;
            max-width: 610px;
            animation: riseIn .9s ease both;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            padding: 9px 13px;
            border: 1px solid rgba(255,255,255,.28);
            border-radius: 50px;
            background: rgba(255,255,255,.13);
            backdrop-filter: blur(12px);
            font-size: 10px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .eyebrow-dot {
            width: 8px;
            height: 8px;
            background: #d5ee91;
            border-radius: 50%;
            box-shadow: 0 0 12px #d5ee91;
        }

        .hero h1 {
            margin: 24px 0 18px;
            font-size: clamp(48px, 6vw, 78px);
            line-height: 1.06;
            letter-spacing: -3.5px;
            font-weight: 600;
        }

        .hero h1 span {
            color: #d9ed9a;
            font-style: italic;
        }

        .hero-description {
            max-width: 440px;
            color: rgba(255,255,255,.87);
            font-size: 14px;
            line-height: 1.9;
        }

        .hero-actions {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 23px;
            margin-top: 29px;
        }

        .primary-btn {
            display: inline-flex;
            justify-content: center;
            align-items: center;
            gap: 13px;
            padding: 15px 22px;
            background: #d4e994;
            color: #263c29;
            border: 0;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 700;
            box-shadow: 0 8px 25px rgba(17,40,27,.13);
            transition: .25s;
        }

        .primary-btn:hover {
            background: #e5f5b3;
            transform: translateY(-3px);
        }

        .video-link {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
        }

        .play-circle {
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            border: 1px solid rgba(255,255,255,.8);
            border-radius: 50%;
            font-size: 12px;
        }

        .social-proof {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 35px;
        }

        .avatar-stack {
            display: flex;
            padding-left: 3px;
        }

        .avatar-stack img {
            width: 30px;
            height: 30px;
            margin-left: -4px;
            object-fit: cover;
            border: 2px solid rgba(255,255,255,.9);
            border-radius: 50%;
        }

        .social-proof p {
            font-size: 10px;
            line-height: 1.7;
            color: rgba(255,255,255,.9);
        }

        .stars {
            color: #e8d17f;
            letter-spacing: 2px;
        }

        /* FLOATING DESTINATION CARDS */

        .destination-stage {
            position: absolute;
            top: 115px;
            right: 3%;
            width: 53%;
            height: 420px;
            perspective: 1200px;
            z-index: 4;
        }

        .orbit {
            position: absolute;
            left: 50%;
            bottom: 15px;
            width: 85%;
            height: 95px;
            border: 1px solid rgba(220,239,157,.7);
            border-radius: 50%;
            transform: translateX(-50%) rotateX(65deg);
            box-shadow: 0 0 25px rgba(207,232,139,.14);
        }

        .orbit::after {
            content: "";
            position: absolute;
            width: 12px;
            height: 12px;
            left: 50%;
            top: -5px;
            border-radius: 50%;
            background: #e1f5a1;
            box-shadow: 0 0 18px #d9f69a;
        }

        .destination-card {
            position: absolute;
            left: 50%;
            top: 47%;
            width: clamp(155px, 19vw, 235px);
            height: clamp(235px, 28vw, 325px);
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.65);
            border-radius: 18px;
            background: #d7dfcb;
            box-shadow: 0 28px 60px rgba(17,37,29,.35);
            transform-style: preserve-3d;
            transition:
                transform .85s cubic-bezier(.2,.75,.25,1),
                opacity .85s ease,
                filter .85s ease;
            will-change: transform;
        }

        .destination-card img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .destination-card::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(
                180deg,
                transparent 45%,
                rgba(20,39,30,.1) 55%,
                rgba(20,39,30,.88) 100%
            );
        }

        .destination-card .card-info {
            position: absolute;
            z-index: 2;
            bottom: 0;
            left: 0;
            width: 100%;
            padding: 17px;
            color: white;
        }

        .card-info .card-tag {
            display: inline-block;
            margin-bottom: 10px;
            padding: 5px 8px;
            border-radius: 30px;
            background: rgba(244,246,225,.2);
            backdrop-filter: blur(8px);
            font-size: 9px;
        }

        .card-info h3 {
            font-family: 'Playfair Display', serif;
            font-size: 25px;
        }

        .card-info p {
            margin-top: 5px;
            color: rgba(255,255,255,.88);
            font-size: 10px;
        }

        .stage-arrow {
            position: absolute;
            z-index: 8;
            top: 47%;
            width: 39px;
            height: 39px;
            border: 0;
            border-radius: 50%;
            background: rgba(255,255,249,.94);
            color: var(--forest);
            font-size: 19px;
            box-shadow: 0 5px 20px rgba(0,0,0,.1);
            transition: .2s;
        }

        .stage-arrow:hover {
            background: #d8ed9e;
            transform: scale(1.08);
        }

        .stage-prev {
            left: 0;
        }

        .stage-next {
            right: 0;
        }

        .stage-label {
            position: absolute;
            right: 0;
            bottom: -25px;
            color: white;
            font-family: 'Playfair Display', serif;
            font-size: 16px;
            font-style: italic;
            transform: rotate(-9deg);
        }

        /* GLASS TRIP FORM */

        .planner-wrap {
            position: relative;
            z-index: 10;
            margin-top: -70px;
        }

        .planner {
            display: grid;
            grid-template-columns: 180px 1fr;
            padding: 22px;
            border: 1px solid rgba(255,255,255,.85);
            border-radius: 28px;
            background: rgba(250,248,239,.89);
            backdrop-filter: blur(22px);
            box-shadow: var(--shadow);
            transform: rotateX(1deg);
        }

        .planner-aside {
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 18px;
            border-right: 1px solid var(--line);
        }

        .compass-icon {
            display: grid;
            place-items: center;
            width: 43px;
            height: 43px;
            margin-bottom: 15px;
            border-radius: 50%;
            background: #e2e9c8;
            color: var(--forest);
            font-size: 23px;
        }

        .planner-aside h2 {
            font-family: 'Playfair Display', serif;
            font-size: 23px;
            line-height: 1.2;
        }

        .planner-aside p {
            margin-top: 10px;
            color: var(--muted);
            font-size: 11px;
            line-height: 1.7;
        }

        .handwriting {
            margin-top: 23px;
            color: var(--olive);
            font-family: 'Playfair Display', serif;
            font-size: 16px;
            font-style: italic;
            transform: rotate(-7deg);
        }

        .planner-form-area {
            padding: 15px 17px 8px 25px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px 15px;
        }

        .field {
            min-width: 0;
        }

        .field label {
            display: block;
            margin-bottom: 8px;
            color: #354337;
            font-size: 10px;
            font-weight: 700;
        }

        .field input,
        .field select {
            width: 100%;
            min-width: 0;
            padding: 12px 11px;
            border: 1px solid #e0dfd4;
            border-radius: 9px;
            outline: none;
            background: rgba(255,255,255,.65);
            color: var(--ink);
            font-size: 11px;
            transition: border .2s, box-shadow .2s;
        }

        .field input:focus,
        .field select:focus {
            border-color: var(--olive);
            box-shadow: 0 0 0 3px rgba(102,121,74,.1);
        }

        .field input::placeholder {
            color: #9ca397;
        }

        .interests-field {
            grid-column: span 2;
        }

        .interest-list {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
        }

        .interest-option input {
            position: absolute;
            opacity: 0;
            pointer-events: none;
        }

        .interest-option span {
            display: inline-block;
            padding: 9px 11px;
            border: 1px solid #e2e1d7;
            border-radius: 7px;
            background: rgba(255,255,255,.5);
            color: #5f6b5d;
            font-size: 10px;
            cursor: pointer;
            transition: .2s;
        }

        .interest-option input:checked + span {
            border-color: var(--olive);
            background: #e1e8ce;
            color: var(--forest);
        }

        .form-submit-area {
            display: flex;
            align-items: end;
        }

        .plan-submit {
            width: 100%;
            padding: 14px 12px;
            border: 0;
            border-radius: 50px;
            background: var(--olive-dark);
            color: white;
            font-size: 11px;
            font-weight: 700;
            transition: .25s;
        }

        .plan-submit:hover {
            background: #506c3e;
            transform: translateY(-2px);
        }

        .plan-submit:disabled {
            opacity: .65;
            cursor: wait;
            transform: none;
        }

        .form-message {
            display: none;
            margin-top: 15px;
            padding: 13px;
            border-radius: 10px;
            font-size: 12px;
            line-height: 1.7;
            overflow-wrap: anywhere;
        }

        .form-message.visible {
            display: block;
        }

        .form-message.success {
            color: #304d2b;
            background: #e8efd9;
            border: 1px solid #cbd9b6;
        }

        .form-message.error {
            color: #883f34;
            background: #f9e9e1;
            border: 1px solid #e9c8ba;
        }

        .form-message.warning {
            color: #775a17;
            background: #fff3cc;
            border: 1px solid #ead58e;
        }

        /* SHARED SECTION STYLES */

        .section {
            padding: 105px 0;
        }

        .section-kicker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 15px;
            color: var(--olive);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.6px;
            text-transform: uppercase;
        }

        .section-kicker span {
            display: grid;
            place-items: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #e4e9d1;
            font-size: 12px;
        }

        .section-title {
            font-family: 'Playfair Display', Georgia, serif;
            font-size: clamp(34px, 4vw, 48px);
            line-height: 1.14;
            letter-spacing: -1.2px;
            font-weight: 600;
        }

        .section-description {
            margin-top: 15px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.9;
        }

        /* FEATURES */

        .features-layout {
            display: grid;
            grid-template-columns: .85fr 1.65fr;
            gap: 45px;
            align-items: center;
        }

        .features-intro {
            max-width: 370px;
        }

        .features-intro .handwriting {
            display: inline-block;
            margin-top: 25px;
            font-size: 19px;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }

        .feature-card {
            min-height: 220px;
            padding: 20px 16px;
            border: 1px solid rgba(255,255,255,.8);
            border-radius: 18px;
            background: rgba(255,255,255,.48);
            box-shadow: 0 10px 30px rgba(52,75,50,.045);
            backdrop-filter: blur(10px);
            transition: transform .3s, background .3s, box-shadow .3s;
        }

        .feature-card:nth-child(2) {
            transform: translateY(-13px);
        }

        .feature-card:nth-child(4) {
            transform: translateY(-5px);
        }

        .feature-card:hover {
            transform: translateY(-8px);
            background: rgba(255,255,255,.78);
            box-shadow: 0 18px 35px rgba(52,75,50,.1);
        }

        .feature-icon {
            display: grid;
            place-items: center;
            width: 46px;
            height: 46px;
            margin-bottom: 17px;
            border-radius: 50%;
            background: #e0ebc4;
            font-size: 21px;
        }

        .feature-card:nth-child(2) .feature-icon {
            background: #e8dff1;
        }

        .feature-card:nth-child(3) .feature-icon {
            background: #f4e1bd;
        }

        .feature-card:nth-child(4) .feature-icon {
            background: #d6e5e4;
        }

        .feature-card h3 {
            font-family: 'Playfair Display', serif;
            font-size: 15px;
            line-height: 1.4;
        }

        .feature-card p {
            margin-top: 12px;
            color: var(--muted);
            font-size: 10px;
            line-height: 1.8;
        }

        /* HOW IT WORKS */

        .journey {
            position: relative;
            padding: 100px 0 110px;
            color: white;
            background: #8b9f88;
            overflow: hidden;
            isolation: isolate;
        }

        .journey-bg {
            position: absolute;
            z-index: -3;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 55%;
        }

        .journey::before {
            content: "";
            position: absolute;
            z-index: -2;
            inset: 0;
            background: linear-gradient(
                90deg,
                rgba(23,52,41,.86),
                rgba(29,55,42,.6) 55%,
                rgba(29,55,42,.15)
            );
        }

        .journey-layout {
            display: grid;
            grid-template-columns: 1.1fr .9fr;
            align-items: center;
            gap: 30px;
        }

        .journey .section-kicker {
            color: #e1efad;
        }

        .journey .section-kicker span {
            background: rgba(255,255,255,.16);
        }

        .journey .section-description {
            color: rgba(255,255,255,.8);
        }

        .steps-panel {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 38px;
            padding: 22px 18px;
            border: 1px solid rgba(255,255,255,.2);
            border-radius: 18px;
            background: rgba(24,45,34,.47);
            backdrop-filter: blur(15px);
        }

        .step {
            position: relative;
            padding: 4px 6px;
        }

        .step-icon {
            display: grid;
            place-items: center;
            width: 45px;
            height: 45px;
            margin-bottom: 14px;
            border-radius: 50%;
            background: #d9e9a7;
            color: var(--forest);
            font-size: 19px;
        }

        .step:nth-child(2) .step-icon {
            background: #d9d4f1;
        }

        .step:nth-child(3) .step-icon {
            background: #eee8ad;
        }

        .step h3 {
            font-size: 11px;
            margin-bottom: 7px;
        }

        .step p {
            color: rgba(255,255,255,.77);
            font-size: 10px;
            line-height: 1.7;
        }

        .journey-photos {
            position: relative;
            min-height: 350px;
            perspective: 900px;
        }

        .photo-print {
            position: absolute;
            width: 210px;
            height: 265px;
            padding: 9px 9px 30px;
            border-radius: 5px;
            background: #fffdf4;
            box-shadow: 0 22px 45px rgba(0,0,0,.28);
            transition: transform .5s ease;
        }

        .photo-print img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .photo-print:first-child {
            top: 35px;
            left: 8%;
            transform: rotate(-8deg);
            animation: floatOne 6s ease-in-out infinite;
        }

        .photo-print:last-child {
            top: 65px;
            right: 5%;
            transform: rotate(8deg);
            animation: floatTwo 6s ease-in-out infinite;
        }

        .photo-caption {
            position: absolute;
            bottom: 8px;
            left: 0;
            width: 100%;
            color: #50614a;
            text-align: center;
            font-family: 'Playfair Display', serif;
            font-size: 11px;
            font-style: italic;
        }

        /* FINAL CTA */

        .final-cta {
            padding: 85px 0;
        }

        .cta-panel {
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 30px;
            padding: 48px;
            border-radius: 25px;
            color: white;
            background: linear-gradient(120deg, #314c35, #6d8051);
            box-shadow: 0 20px 50px rgba(47,70,42,.16);
        }

        .cta-panel::after {
            content: "✳";
            position: absolute;
            right: 18%;
            top: -75px;
            color: rgba(255,255,255,.07);
            font-size: 260px;
            pointer-events: none;
        }

        .cta-panel h2 {
            position: relative;
            z-index: 1;
            max-width: 590px;
            font-family: 'Playfair Display', serif;
            font-size: clamp(30px, 4vw, 45px);
            line-height: 1.2;
        }

        .cta-panel p {
            position: relative;
            z-index: 1;
            margin-top: 12px;
            color: rgba(255,255,255,.78);
            font-size: 12px;
        }

        .cta-panel .primary-btn {
            position: relative;
            z-index: 2;
            flex-shrink: 0;
        }

        /* FOOTER */

        .footer {
            padding: 27px 0;
            background: #203a2d;
            color: rgba(255,255,255,.8);
        }

        .footer-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 22px;
        }

        .footer .logo {
            font-size: 17px;
            color: white;
        }

        .footer .logo-mark {
            width: 30px;
            height: 30px;
            font-size: 18px;
        }

        .footer-note {
            font-size: 10px;
            color: rgba(255,255,255,.65);
        }

        .footer-links {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 11px;
        }

        .footer-links a:hover {
            color: #d9ed9a;
        }

        /* ANIMATIONS */

        @keyframes riseIn {
            from {
                opacity: 0;
                transform: translateY(22px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes sceneryReveal {
            from {
                transform: scale(1.05);
                filter: saturate(.8);
            }
            to {
                transform: scale(1);
                filter: saturate(1);
            }
        }

        @keyframes floatOne {
            0%, 100% { translate: 0 0; }
            50% { translate: 0 -10px; }
        }

        @keyframes floatTwo {
            0%, 100% { translate: 0 0; }
            50% { translate: 0 10px; }
        }

        /* RESPONSIVE DESIGN */

        @media (max-width: 1000px) {
            .destination-stage {
                right: 0;
                width: 54%;
                transform: scale(.88);
                transform-origin: center right;
            }

            .hero-content {
                width: 53%;
            }

            .planner {
                grid-template-columns: 145px 1fr;
                padding: 14px;
            }

            .planner-aside {
                padding: 12px;
            }

            .planner-form-area {
                padding: 12px;
            }

            .features-layout {
                grid-template-columns: 1fr;
                gap: 35px;
            }

            .features-intro {
                max-width: 570px;
            }

            .feature-card {
                min-height: 200px;
            }
        }

        @media (max-width: 720px) {
            .container {
                width: calc(100% - 36px);
            }

            .navbar {
                padding: 17px 0;
            }

            .nav-links {
                gap: 15px;
            }

            .nav-links a:not(.nav-button) {
                display: none;
            }

            .nav-button {
                padding: 11px 14px;
                font-size: 11px;
            }

            .hero {
                padding: 120px 0 360px;
                min-height: 900px;
            }

            .hero-content {
                width: 100%;
                max-width: 540px;
            }

            .hero h1 {
                font-size: clamp(46px, 10vw, 66px);
                letter-spacing: -2.5px;
            }

            .hero-description {
                font-size: 13px;
            }

            .destination-stage {
                top: auto;
                bottom: 68px;
                left: 50%;
                right: auto;
                width: 100%;
                height: 340px;
                transform: translateX(-50%) scale(.88);
                transform-origin: center bottom;
            }

            .destination-card {
                width: 180px;
                height: 255px;
            }

            .stage-arrow {
                width: 35px;
                height: 35px;
            }

            .planner-wrap {
                margin-top: -35px;
            }

            .planner {
                grid-template-columns: 1fr;
                padding: 20px;
                border-radius: 22px;
            }

            .planner-aside {
                display: grid;
                grid-template-columns: 45px 1fr;
                column-gap: 13px;
                padding: 0 0 18px;
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }

            .compass-icon {
                grid-row: span 2;
                margin: 0;
            }

            .planner-aside h2 {
                font-size: 21px;
            }

            .planner-aside p {
                margin-top: 4px;
            }

            .handwriting {
                display: none;
            }

            .planner-form-area {
                padding: 20px 0 0;
            }

            .form-grid {
                grid-template-columns: 1fr 1fr;
                gap: 15px 11px;
            }

            .interests-field {
                grid-column: 1 / -1;
            }

            .form-submit-area {
                grid-column: 1 / -1;
            }

            .section {
                padding: 75px 0;
            }

            .feature-grid {
                grid-template-columns: 1fr 1fr;
            }

            .feature-card,
            .feature-card:nth-child(2),
            .feature-card:nth-child(4) {
                min-height: 190px;
                transform: none;
            }

            .journey-layout {
                grid-template-columns: 1fr;
            }

            .journey-photos {
                min-height: 325px;
            }

            .photo-print {
                width: 180px;
                height: 235px;
            }

            .steps-panel {
                padding: 16px 10px;
                gap: 7px;
            }

            .step {
                padding: 3px;
            }

            .step h3 {
                font-size: 10px;
            }

            .cta-panel {
                align-items: flex-start;
                flex-direction: column;
                padding: 32px 25px;
            }

            .footer-inner {
                flex-direction: column;
                text-align: center;
            }
        }

        @media (max-width: 420px) {
            .hero {
                padding-bottom: 330px;
            }

            .hero h1 {
                font-size: 43px;
            }

            .destination-stage {
                bottom: 60px;
                transform: translateX(-50%) scale(.76);
                width: 125%;
            }

            .form-grid {
                grid-template-columns: 1fr;
            }

            .interests-field,
            .form-submit-area {
                grid-column: auto;
            }

            .interest-option span {
                padding: 8px 9px;
            }

            .feature-grid {
                gap: 10px;
            }

            .feature-card {
                padding: 15px 12px;
            }

            .steps-panel {
                grid-template-columns: 1fr;
                gap: 20px;
            }

            .step {
                display: grid;
                grid-template-columns: 43px 1fr;
                column-gap: 12px;
            }

            .step-icon {
                grid-row: span 2;
                margin-bottom: 0;
            }

            .step p {
                margin-top: 3px;
            }

            .photo-print {
                width: 155px;
                height: 210px;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            html {
                scroll-behavior: auto;
            }

        }
        /* ==========================================
   AI-GENERATED TRIP RESULTS
========================================== */

.trip-result {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100vh;
    height: 100dvh;
    margin: 0;
    padding: 0;
    overflow: hidden;
    border: 0;
    border-radius: 0;
    background: var(--cream);
    box-shadow: none;
}

.trip-result[hidden] {
    display: none !important;
}

body.trip-scene-open {
    overflow: hidden;
}

.trip-scene-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 18px clamp(18px, 3vw, 42px);
    border-bottom: 1px solid var(--line);
    background: var(--paper);
}

.trip-result-header {
    min-width: 0;
    margin: 0;
}

.trip-result-header .section-kicker {
    margin-bottom: 2px;
}

.trip-result-header .section-title {
    margin-top: 0;
    font-size: clamp(23px, 2.4vw, 34px);
}

.trip-result-header .section-description {
    margin-top: 4px;
}

.trip-scene-close {
    flex: 0 0 auto;
    padding: 10px 16px;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--forest);
    background: white;
    font: inherit;
    font-weight: 700;
}

.trip-scene-message {
    display: none;
    padding: 10px clamp(18px, 3vw, 42px);
    color: #883f34;
    background: #f9e9e1;
    line-height: 1.5;
}

.trip-scene-message.visible {
    display: block;
}

.trip-scene-message.warning {
    color: #775a17;
    background: #fff3cc;
}

.trip-scene-loading {
    margin: 20px 0;
    padding: 18px;
    border-radius: 14px;
    color: var(--forest);
    background: #edf3ee;
    font-weight: 700;
}

.trip-scene-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
    grid-template-rows: minmax(0, 1fr);
    flex: 1;
    min-height: 0;
}

.trip-result-header {
    margin-bottom: 0;
}

.trip-result-header .section-title {
    margin-top: 8px;
}

.recommendation-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px;
    margin: 24px 0 32px;
}

.recommendation-card {
    overflow: hidden;
    border: 1px solid rgba(24, 59, 47, .14);
    border-radius: 16px;
    background: #fff;
}

.recommendation-card img {
    display: block;
    width: 100%;
    height: 150px;
    object-fit: cover;
    background: #e8eee9;
}

.recommendation-content { padding: 16px; }
.recommendation-content h3 { margin: 0 0 8px; }
.recommendation-content p { margin: 8px 0; line-height: 1.5; }
.recommendation-cost { font-weight: 700; }
.recommendation-source { font-size: .85rem; }
.recommendation-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.recommendation-actions button, .feedback-controls button {
    border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer;
    color: #fff; background: var(--forest); font: inherit;
}
.feedback-panel { margin: 12px 0 26px; padding: 18px; border-radius: 14px; background: #edf3ee; }
.feedback-panel label { display: block; margin-bottom: 8px; font-weight: 700; }
.feedback-controls { display: flex; gap: 10px; }
.feedback-controls input { flex: 1; min-width: 0; padding: 10px 12px; border: 1px solid #b9c9bd; border-radius: 8px; font: inherit; }
#routeSection h3 { margin-bottom: 10px; color: var(--forest); }
#routeSection p { margin: 8px 0; line-height: 1.55; }
#routeModes { margin: 12px 0; padding-left: 22px; }
#routeModes li { margin: 8px 0; line-height: 1.5; }
#routeLegs { display: grid; gap: 10px; margin: 14px 0; padding-left: 24px; }
#routeLegs li { padding: 12px 14px; border-radius: 10px; background: rgba(255,255,255,.7); line-height: 1.5; }
#routeCostSegments { display: grid; gap: 8px; margin: 10px 0; padding-left: 22px; }
#routeCostSegments li { line-height: 1.5; }
#routeLegs strong { color: var(--forest); }
#routeSection .feedback-controls { flex-wrap: wrap; margin-top: 12px; }
#routeSection a { color: var(--forest); font-weight: 700; text-decoration: underline; }
#routeMap { height: 340px; margin: 14px 0; border-radius: 12px; background: #e5ece5; }
#routeMapStatus { font-size: .95rem; color: var(--muted); }
.daily-plan-grid { display: grid; gap: 16px; margin: 20px 0; }
.daily-plan-card, .hotel-choice { padding: 18px; border: 1px solid rgba(24,59,47,.14); border-radius: 14px; background: #fff; }
.daily-plan-card h3, .hotel-choice h4 { margin-top: 0; color: var(--forest); }
.day-transport { margin: 12px 0 16px; padding: 12px 14px; border-left: 4px solid var(--olive); border-radius: 8px; background: #edf3ee; line-height: 1.5; }
.day-transport strong { display: block; margin-bottom: 4px; color: var(--forest); }
.day-transport span { display: block; margin-top: 6px; }
.attraction-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.attraction-card { overflow: hidden; border-radius: 10px; background: #f2f5f2; }
.attraction-card img { width: 100%; height: 150px; object-fit: cover; display: block; }
.attraction-card div { padding: 12px; }
.attraction-card h4 { margin: 0 0 6px; }
.attraction-card p { margin: 6px 0; line-height: 1.45; }
.hotel-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 16px 0 26px; }
.chat-messages {
    display: grid;
    align-content: start;
    flex: 1 1 0;
    gap: 10px;
    min-height: 160px;
    max-height: none;
    overflow-y: auto;
    margin: 10px 0;
    padding: 12px;
    border: 1px solid rgba(24, 59, 47, .09);
    border-radius: 12px;
    background: rgba(255,255,255,.62);
}
.chat-messages:empty::before {
    align-self: center;
    justify-self: center;
    max-width: 230px;
    color: var(--muted);
    content: "Your conversation will appear here. Ask TripMate anything about your trip.";
    font-size: 13px;
    line-height: 1.6;
    text-align: center;
}
.chat-message { max-width: 94%; padding: 12px 14px; border-radius: 12px; background: #fff; line-height: 1.5; overflow-wrap: anywhere; }
.chat-message.user { margin-left: auto; color: #fff; background: var(--forest); }
.chat-message a { color: inherit; font-weight: 700; }
.chat-question-prompts { margin: 0; }
.chat-question-prompts summary { width: fit-content; color: var(--forest); font-size: 13px; font-weight: 700; cursor: pointer; }
.chat-question-list { display: flex; flex-wrap: wrap; gap: 8px; max-height: 100px; margin-top: 8px; overflow-y: auto; }
.chat-question-prompts button { border: 1px solid #b9c9bd; border-radius: 999px; padding: 8px 12px; color: var(--forest); background: #fff; cursor: pointer; font: inherit; }

.trip-chat-sidebar {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    padding: clamp(16px, 2vw, 28px);
    overflow: hidden;
    border-right: 1px solid var(--line);
    background: #eef3eb;
}

.trip-chat-sidebar .feedback-panel {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: clamp(14px, 1.5vw, 20px);
    min-height: 0;
    height: 100%;
    box-sizing: border-box;
    overflow: hidden;
    border: 1px solid rgba(24, 59, 47, .08);
    background: rgba(255, 255, 255, .72);
}

.trip-chat-sidebar .feedback-panel > h3 {
    margin: 0;
}

.trip-chat-sidebar .feedback-panel > #chatIntro {
    margin: 0;
    line-height: 1.5;
}

.trip-chat-sidebar .feedback-panel > h3,
.trip-chat-sidebar .feedback-panel > p,
.trip-chat-sidebar .chat-question-prompts,
.trip-chat-sidebar .feedback-controls {
    flex: 0 0 auto;
}

.trip-chat-sidebar .chat-question-prompts {
    flex: 0 0 auto;
}

.trip-chat-sidebar .chat-question-list {
    max-height: 104px;
}

.trip-chat-sidebar .chat-question-prompts button {
    padding: 7px 10px;
    font-size: 13px;
}

.trip-chat-sidebar .chat-messages {
    margin: 4px 0;
}

.trip-chat-sidebar .feedback-controls input {
    min-height: 46px;
}

.trip-chat-sidebar .feedback-controls button {
    flex: 0 0 auto;
    min-width: 68px;
}

.trip-main-details {
    min-width: 0;
    min-height: 0;
    padding: clamp(18px, 2.5vw, 36px);
    overflow-y: auto;
    scroll-behavior: smooth;
}

.trip-main-details > #recommendationGrid,
.trip-main-details > .feedback-panel,
.trip-main-details > section,
.trip-main-details > .trip-itinerary,
.trip-main-details > .trip-note,
.trip-main-details > .trip-result-actions {
    margin-bottom: 24px;
}

.trip-main-details > #dailyPlanSection > h3 {
    margin-bottom: 14px;
    color: var(--forest);
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 24px;
}

.trip-itinerary {
    color: var(--ink);
    font-size: 14px;
    line-height: 1.85;
    overflow-wrap: anywhere;
}

.trip-itinerary h1,
.trip-itinerary h2,
.trip-itinerary h3,
.trip-itinerary h4 {
    margin: 24px 0 10px;
    color: var(--forest);
    font-family: 'Playfair Display', Georgia, serif;
    line-height: 1.35;
}

.trip-itinerary h1 {
    font-size: 28px;
}

.trip-itinerary h2 {
    font-size: 23px;
}

.trip-itinerary h3 {
    font-size: 19px;
}

.trip-itinerary h4 {
    font-size: 16px;
}

.trip-itinerary p {
    margin: 10px 0;
}

.trip-itinerary ul,
.trip-itinerary ol {
    margin: 10px 0 16px 24px;
}

.trip-itinerary li {
    margin: 6px 0;
    padding-left: 3px;
}

.trip-itinerary strong {
    color: var(--forest);
}

.trip-itinerary em {
    color: var(--olive-dark);
}

.trip-itinerary hr {
    margin: 22px 0;
    border: 0;
    border-top: 1px solid var(--line);
}

.trip-note {
    margin-top: 24px;
    padding: 15px 17px;
    border-radius: 12px;
    background: #e8efd9;
    color: #405438;
    font-size: 12px;
    line-height: 1.8;
}

.trip-result-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 22px;
}
#tripResultActions[hidden] { display: none !important; }
.feedback-panel > input { box-sizing: border-box; width: min(100%, 560px); margin: 6px 0 12px; padding: 10px 12px; border: 1px solid #b9c9bd; border-radius: 8px; font: inherit; }

.result-action {
    padding: 12px 18px;
    border: 1px solid var(--olive-dark);
    border-radius: 30px;
    background: var(--olive-dark);
    color: white;
    font-size: 12px;
    font-weight: 700;
    transition: .2s;
}

.result-action:hover {
    background: var(--olive);
    transform: translateY(-2px);
}

@media (max-width: 760px) {
    .trip-scene-layout {
        grid-template-columns: minmax(0, 1fr);
        grid-template-rows: minmax(390px, 58vh) minmax(0, 1fr);
    }

    .trip-chat-sidebar {
        padding: 12px 16px;
        overflow: hidden;
        border-right: 0;
        border-bottom: 1px solid var(--line);
    }

    .trip-chat-sidebar .feedback-panel {
        padding: 14px;
    }

    .chat-messages {
        min-height: 72px;
        margin: 8px 0;
    }

    .trip-chat-sidebar .chat-question-list {
        max-height: 56px;
    }

    .trip-chat-sidebar .chat-messages {
        min-height: 80px;
        margin: 0;
    }

    .trip-chat-sidebar .feedback-controls input {
        min-height: 40px;
    }

    .trip-main-details {
        padding: 16px;
    }

    .trip-scene-topbar {
        padding: 12px 16px;
    }

    .trip-scene-close {
        padding: 8px 12px;
    }

    .trip-result-header .section-description {
        font-size: 11px;
    }

    .trip-itinerary h1 {
        font-size: 24px;
    }

    .trip-itinerary h2 {
        font-size: 21px;
    }

    .trip-result-actions {
        flex-direction: column;
    }

    .result-action {
        width: 100%;
    }
}

@media print {
    body * {
        visibility: hidden;
    }

    #tripResult,
    #tripResult * {
        visibility: visible;
    }

    #tripResult {
        position: absolute;
        inset: 0;
        width: 100%;
        margin: 0;
        padding: 20px;
        border: none;
        box-shadow: none;
        background: white;
    }

    .trip-result-actions {
        display: none;
    }
}
    </style>
</head>

<body>
    <header class="navbar">
        <div class="container nav-inner">
            <a href="{{ route('home') }}" class="logo">
                <span class="logo-mark"><span>▲</span></span>
                <span>TripMateAI</span>
            </a>

            <nav class="nav-links" aria-label="Main navigation">
                <a href="#home">Home</a>
                <a href="#destinations">Explore</a>
                <a href="#features">Features</a>
                <a href="#how-it-works">About</a>
                @auth
                    <span>{{ Auth::user()->name }}</span>
                    <form method="post" action="{{ route('logout') }}" style="display:inline">@csrf<button type="submit" class="nav-button">Sign out</button></form>
                @else
                    <a href="{{ route('login') }}">Sign in</a>
                    <a href="{{ route('register') }}" class="nav-button">Sign up</a>
                @endauth
                <a href="#planner" class="nav-button">Plan Your Trip ↗</a>
            </nav>
        </div>
    </header>

    <main>
        <!-- HERO SECTION -->
        <section class="hero" id="home">
            <img
                class="hero-bg"
                src="https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=2200&q=90"
                alt=""
                fetchpriority="high"
            >

            <div class="container">
                <div class="hero-content">
                    <div class="eyebrow">
                        <span class="eyebrow-dot"></span>
                        AI powered travel planner
                    </div>

                    <h1 class="serif">
                        Explore<br>
                        Dream Destinations<br>
                        <span>With AI</span>
                    </h1>

                    <p class="hero-description">
                        Share your budget, dates, and interests. TripMate AI
                        is designed to help you plan personalized journeys
                        and discover places that fit your travel style.
                    </p>

                    <div class="hero-actions">
                        <a href="#planner" class="primary-btn">
                            Start Planning <span>→</span>
                        </a>

                        <a href="#how-it-works" class="video-link">
                            <span class="play-circle">▶</span>
                            How it works
                        </a>
                    </div>

                    <div class="social-proof">
                        <div class="avatar-stack">
                            <img src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=80&q=80" alt="">
                            <img src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=80&q=80" alt="">
                            <img src="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=80&q=80" alt="">
                            <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=80&q=80" alt="">
                        </div>

                        <p>
                            Your next adventure starts here<br>
                            <span class="stars">★★★★★</span>
                        </p>
                    </div>
                </div>
            </div>

            <!-- ROTATING 3D DESTINATION CARDS -->
            <div class="destination-stage" id="destinations">
                <div class="orbit"></div>

                <button type="button" class="stage-arrow stage-prev"
                        id="destinationPrev" aria-label="Previous destination">‹</button>

                <article class="destination-card">
                    <img src="https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=700&q=85" alt="Green tropical landscape in Bali">
                    <div class="card-info">
                        <span class="card-tag">Nature · Culture</span>
                        <h3>Bali</h3>
                        <p>Find your island rhythm</p>
                    </div>
                </article>

                <article class="destination-card">
                    <img src="https://images.unsplash.com/photo-1514282401047-d79a71a590e8?auto=format&fit=crop&w=700&q=85" alt="Turquoise ocean in the Maldives">
                    <div class="card-info">
                        <span class="card-tag">Ocean · Escape</span>
                        <h3>Maldives</h3>
                        <p>Slow down by the sea</p>
                    </div>
                </article>

                <article class="destination-card">
                    <img src="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=90" alt="Traditional Japanese street">
                    <div class="card-info">
                        <span class="card-tag">Culture · Nature</span>
                        <h3>Japan</h3>
                        <p>Tradition meets tomorrow</p>
                    </div>
                </article>

                <article class="destination-card">
                    <img src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=700&q=85" alt="Beautiful mountain travel scenery">
                    <div class="card-info">
                        <span class="card-tag">Adventure · Views</span>
                        <h3>Highlands</h3>
                        <p>Take the scenic route</p>
                    </div>
                </article>

                <article class="destination-card">
                    <img src="https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=700&q=85" alt="London cityscape">
                    <div class="card-info">
                        <span class="card-tag">City · Discovery</span>
                        <h3>London</h3>
                        <p>A city full of stories</p>
                    </div>
                </article>

                <button type="button" class="stage-arrow stage-next"
                        id="destinationNext" aria-label="Next destination">›</button>

                <div class="stage-label">Discover the world ✧</div>
            </div>
        </section>

        <!-- TRIP PLANNER -->
        <section class="container planner-wrap" id="planner">
            <div class="planner">
                <aside class="planner-aside">
                    <div class="compass-icon">◎</div>
                    <h2>Plan Your<br>Perfect Trip</h2>
                    <p>Let's turn your travel ideas into reality.</p>
                    <div class="handwriting">Adventure awaits →</div>
                </aside>

                <div class="planner-form-area">
                    <form id="tripForm">
                        <div class="form-grid">
                            <div class="field">
                                <label for="trip_type">◉ &nbsp; Tour Type</label>
                                <select id="trip_type" name="trip_type" required>
                                    <option value="single">Single tour</option>
                                    <option value="group">Group tour</option>
                                </select>
                            </div>

                            <div class="field">
                                <label id="budgetLabel" for="budget">◈ &nbsp; Your Budget</label>
                                <input type="number" id="budget" name="budget"
                                       min="1" step="any" placeholder="e.g. 20000" required>
                            </div>

                            <div class="field">
                                <label for="currency">◷ &nbsp; Currency</label>
                                <select id="currency" name="currency" required>
                                    <option value="BDT">BDT — Bangladeshi Taka</option>
                                    <option value="USD">USD — US Dollar</option>
                                </select>
                            </div>

                            <div class="field group-only" id="groupSizeField" hidden>
                                <label for="travelers">♧ &nbsp; Group Members</label>
                                <input type="number" id="travelers" name="travelers"
                                       min="2" max="100" step="1" value="2" disabled>
                            </div>

                            <div class="field group-only" id="contributionField" hidden>
                                <label for="contribution_per_person">◈ &nbsp; Contribution Per Member</label>
                                <input type="number" id="contribution_per_person" name="contribution_per_person"
                                       min="1" step="any" placeholder="e.g. 5000" disabled>
                            </div>

                            <div class="field">
                                <label for="duration_days">▣ &nbsp; Trip Duration</label>
                                <select id="duration_days" name="duration_days" required>
                                    <option value="1">1 day</option>
                                    <option value="2">2 days</option>
                                    <option value="3">3 days</option>
                                    <option value="5">5 days</option>
                                    <option value="7" selected>7 days</option>
                                    <option value="10">10 days</option>
                                    <option value="14">14 days</option>
                                    <option value="21">21 days</option>
                                    <option value="30">30 days</option>
                                </select>
                            </div>

                            <div class="field">
                                <label for="departure_city">⌖ &nbsp; Starting City</label>
                                <input type="text" id="departure_city"
                                       name="departure_city" placeholder="e.g. Dhaka" required>
                            </div>

                            <div class="field">
                                <label for="start_date">▣ &nbsp; Departure Date</label>
                                <input type="date" id="start_date"
                                       name="start_date" required>
                            </div>

                            <div class="field">
                                <label for="travel_scope">◎ &nbsp; Travel Scope</label>
                                <select id="travel_scope" name="travel_scope" required>
                                    <option value="anywhere">Anywhere — surprise me</option>
                                    <option value="local">Bangladesh</option>
                                    <option value="international">International</option>
                                </select>
                            </div>

                            <div class="field interests-field">
                                <label>✿ &nbsp; What kind of trip do you love?</label>

                                <div class="interest-list">
                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="Nature">
                                        <span>♧ Nature</span>
                                    </label>

                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="Mountains">
                                        <span>△ Mountains</span>
                                    </label>

                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="Beach">
                                        <span>♧ Beach</span>
                                    </label>

                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="Adventure">
                                        <span>↗ Adventure</span>
                                    </label>

                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="History and Culture">
                                        <span>⌂ History & Culture</span>
                                    </label>

                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="Food">
                                        <span>♨ Food</span>
                                    </label>

                                    <label class="interest-option">
                                        <input type="checkbox" name="interests[]" value="Relaxation">
                                        <span>☼ Relaxation</span>
                                    </label>
                                </div>
                            </div>

                            <div class="form-submit-area">
                                <button type="submit" class="plan-submit" id="submitBtn">
                                    Plan My Adventure →
                                </button>
                            </div>
                        </div>

                                        <div id="formMessage" class="form-message"
                                             role="status" aria-live="polite"></div>
                                    </form>
                                </div>
                            </div>
                        </section>

<!-- AI-GENERATED TRIP RESULTS -->
<section id="tripResult" class="trip-result" role="dialog" aria-modal="true" aria-labelledby="tripResultTitle" hidden>
    <header class="trip-scene-topbar">
                        <div class="trip-result-header">
                            <span class="section-kicker">✳ Your personalized journey</span>
                            <h2 id="tripResultTitle" class="section-title">Explore trip options</h2>
                            <p id="tripSummary" class="section-description"></p>
                        </div>
                        <button type="button" id="closeTripScene" class="trip-scene-close">← Back to planner</button>
    </header>
    <div id="tripSceneMessage" class="trip-scene-message" role="status" aria-live="polite"></div>
    <div class="trip-scene-layout">
                        <aside class="trip-chat-sidebar">
                            <section id="tripChatSection" class="feedback-panel">
                                <h3>Chat with TripMate</h3>
                                <p id="chatIntro">Choose a destination to start a conversation about your trip. Guests get five free assistant messages.</p>
                                <div id="chatMessages" class="chat-messages" role="log" aria-live="polite"></div>
                                <details class="chat-question-prompts">
                                    <summary>Suggested questions</summary>
                                    <div class="chat-question-list" aria-label="Suggested destination questions">
                    <button type="button" data-trip-question="Is this place safe for families?">Family safety</button>
                    <button type="button" data-trip-question="What food is famous there?">Famous food</button>
                    <button type="button" data-trip-question="Is it suitable during the rainy season?">Rainy season</button>
                    <button type="button" data-trip-question="How much will transportation cost?">Transport cost</button>
                    <button type="button" data-trip-question="Are there affordable hotels?">Affordable hotels</button>
                    <button type="button" data-trip-question="Is this destination crowded?">Crowds</button>
                    <button type="button" data-trip-question="What clothes should I take?">What to pack</button>
                    <button type="button" data-trip-question="What can I do there?">Things to do</button>
                                    </div>
                                </details>
                <div class="feedback-controls">
                    <input id="chatMessageInput" type="text" maxlength="500" placeholder="Ask about this destination">
                    <button type="button" id="sendChatMessageButton">Send</button>
                </div>
            </section>
        </aside>
        <main class="trip-main-details" id="tripMainDetails">
            <div id="tripSceneLoading" class="trip-scene-loading" role="status" hidden>Finding destinations that fit your trip...</div>
            <div id="recommendationGrid" aria-label="Recommended destinations">
                <section id="withinBudgetSection"><h3>Options within your budget</h3><div id="withinBudgetGrid" class="recommendation-grid"></div></section>
                <section id="stretchSection"><h3>Stretch your budget for these</h3><div id="stretchGrid" class="recommendation-grid"></div></section>
            </div>
            <section id="destinationChoicePanel" class="feedback-panel" hidden>
                <label id="destinationChoiceQuestion">Is this your first visit?</label>
                <div class="feedback-controls">
                    <button type="button" id="firstVisitButton">First visit</button>
                    <button type="button" id="repeatVisitButton">I’ve visited before</button>
                </div>
                <div id="visitedPlacesPanel" hidden>
                    <label for="visitedPlacesInput">Which places have you already visited? Separate them with commas.</label>
                    <input id="visitedPlacesInput" type="text" maxlength="500" placeholder="For example: Lalbagh Fort, Ahsan Manzil">
                    <button type="button" id="buildVisitedPlanButton">Plan new places</button>
                </div>
            </section>
            <div class="feedback-panel">
                <label for="tripFeedback">Want different options? Tell TripMate what to change.</label>
                <div class="feedback-controls">
                    <input id="tripFeedback" type="text" maxlength="300" placeholder="For example: quieter places, less travel, or lower cost">
                    <button type="button" id="changeOptionsBtn">Change options</button>
                </div>
            </div>
            <section id="dailyPlanSection" hidden>
                <h3>Places to visit each day</h3>
                <div id="dailyPlanGrid" class="daily-plan-grid"></div>
            </section>
            <section id="routeSection" class="feedback-panel" hidden>
                <h3 id="routeHeading">Route and transport</h3>
                <p id="routeBestVehicle"></p>
                <p id="routeRecommendation"></p>
                <ol id="routeLegs"></ol>
                <ul id="routeModes"></ul>
                <p id="routeEstimate"></p>
                <ol id="routeCostSegments"></ol>
                <p id="routeMapStatus"></p>
                <div id="routeMap" role="img" aria-label="OpenStreetMap route map" hidden></div>
                <p id="routeNote"></p>
                <div class="feedback-controls">
                    <a id="routeMapLink" target="_blank" rel="noopener noreferrer">View route on OpenStreetMap</a>
                </div>
            </section>
            <section id="hotelSection" hidden>
                <h3>Stay options within your accommodation budget</h3>
                <p id="hotelBudgetNote" class="section-description"></p>
                <div id="hotelOptions" class="hotel-options"></div>
            </section>
            <div id="tripItinerary" class="trip-itinerary"></div>
            <p id="tripNote" class="trip-note"></p>
            <div id="tripResultActions" class="trip-result-actions" hidden>
                <button type="button" id="copyItineraryBtn" class="result-action">Copy Itinerary</button>
                <button type="button" id="printItineraryBtn" class="result-action">Print Itinerary</button>
            </div>
        </main>
    </div>
</section>

        <!-- FEATURES -->
        <section class="section" id="features">
            <div class="container features-layout">
                <div class="features-intro">
                    <div class="section-kicker">
                        <span>✳</span> Why TripMate AI?
                    </div>

                    <h2 class="section-title">
                        Smart Planning<br>for Real Journeys
                    </h2>

                    <p class="section-description">
                        Bring your travel ideas together in one place.
                        Start with your preferences and budget, then build
                        toward a journey that feels right for you.
                    </p>

                    <div class="handwriting">More than just a trip ↗</div>
                </div>

                <div class="feature-grid">
                    <article class="feature-card">
                        <div class="feature-icon">◎</div>
                        <h3>Personalized Itineraries</h3>
                        <p>Plan around your interests, budget and travel style.</p>
                    </article>

                    <article class="feature-card">
                        <div class="feature-icon">▣</div>
                        <h3>Travel Research</h3>
                        <p>Designed to support destination and travel information research.</p>
                    </article>

                    <article class="feature-card">
                        <div class="feature-icon">◉</div>
                        <h3>Budget Friendly</h3>
                        <p>Make your budget an important part of the planning process.</p>
                    </article>

                    <article class="feature-card">
                        <div class="feature-icon">✧</div>
                        <h3>AI Assisted</h3>
                        <p>Build toward helpful suggestions shaped around your preferences.</p>
                    </article>
                </div>
            </div>
        </section>

        <!-- HOW IT WORKS -->
        <section class="journey" id="how-it-works">
            <img
                class="journey-bg"
                src="https://images.unsplash.com/photo-1472396961693-142e6e269027?auto=format&fit=crop&w=2000&q=85"
                alt=""
                loading="lazy"
            >

            <div class="container journey-layout">
                <div>
                    <div class="section-kicker">
                        <span>✳</span> How it works
                    </div>

                    <h2 class="section-title">
                        From Your Idea<br>to Your Itinerary
                    </h2>

                    <p class="section-description">
                        You tell us what you want. The application
                        passes your request through the travel-planning
                        service and returns its response.
                    </p>

                    <div class="steps-panel">
                        <article class="step">
                            <div class="step-icon">♙</div>
                            <h3>1. You Share</h3>
                            <p>Your preferences, budget and dates.</p>
                        </article>

                        <article class="step">
                            <div class="step-icon">▤</div>
                            <h3>2. Laravel</h3>
                            <p>Validates your form and forwards it to Python.</p>
                        </article>

                        <article class="step">
                            <div class="step-icon">⌘</div>
                            <h3>3. Python Agent</h3>
                            <p>Receives the request and returns a response.</p>
                        </article>
                    </div>
                </div>

                <div class="journey-photos" aria-label="Travel inspiration photos">
                    <div class="photo-print">
                        <img
                            src="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=600&q=85"
                            alt="Japanese traditional architecture"
                            loading="lazy"
                        >
                        <div class="photo-caption">Real places, real experiences.</div>
                    </div>

                    <div class="photo-print">
                        <img
                            src="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=600&q=85"
                            alt="Mountain peaks above the clouds"
                            loading="lazy"
                        >
                        <div class="photo-caption">Take the scenic route.</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- CALL TO ACTION -->
        <section class="container final-cta">
            <div class="cta-panel">
                <div>
                    <h2 class="serif">The world is waiting for your next story.</h2>
                    <p>Start with an idea. Let the journey take shape.</p>
                </div>

                <a href="#planner" class="primary-btn">
                    Plan Your Trip ↗
                </a>
            </div>
        </section>
    </main>

    <!-- FOOTER -->
    <footer class="footer">
        <div class="container footer-inner">
            <a href="{{ route('home') }}" class="logo">
                <span class="logo-mark"><span>▲</span></span>
                <span>TripMateAI</span>
            </a>

            <p class="footer-note">Thoughtful journeys, powered by technology.</p>

            <nav class="footer-links" aria-label="Footer navigation">
                <a href="#home">Home</a>
                <a href="#features">Features</a>
                <a href="#how-it-works">About</a>
                <a href="#planner">Plan a trip</a>
            </nav>

            <span class="footer-note">© {{ date('Y') }} TripMate AI</span>
        </div>
    </footer>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // ==========================================
        // AUTOMATIC 3D DESTINATION CAROUSEL
        // ==========================================

        const stage = document.querySelector('.destination-stage');
        const destinationCards = [
            ...document.querySelectorAll('.destination-card')
        ];

        const prevDestination = document.getElementById('destinationPrev');
        const nextDestination = document.getElementById('destinationNext');

        let currentDestination = 2;
        let carouselTimer = null;
        let swipeStartX = 0;

        function renderDestinations() {
            const total = destinationCards.length;
            const isMobile = window.innerWidth <= 720;

            destinationCards.forEach((card, index) => {
                let offset = index - currentDestination;

                if (offset > total / 2) offset -= total;
                if (offset < -total / 2) offset += total;

                const distance = Math.abs(offset);
                const xSpacing = isMobile ? 142 : 190;
                const rotation = offset * -19;
                const depth = distance === 0 ? 65 : -distance * 30;
                const scale = Math.max(0.67, 1 - distance * 0.13);

                card.style.transform = `
                    translate(-50%, -50%)
                    translateX(${offset * xSpacing}px)
                    translateZ(${depth}px)
                    rotateY(${rotation}deg)
                    rotateZ(${offset * -1.5}deg)
                    scale(${scale})
                `;

                card.style.opacity = distance > 2 ? '0' :
                    distance === 2 ? '.48' : '1';

                card.style.zIndex = String(10 - distance);
                card.style.pointerEvents = distance > 1 ? 'none' : 'auto';
                card.setAttribute('aria-hidden', distance > 1 ? 'true' : 'false');
            });
        }

        function goNext() {
            currentDestination =
                (currentDestination + 1) % destinationCards.length;
            renderDestinations();
        }

        function goPrevious() {
            currentDestination =
                (currentDestination - 1 + destinationCards.length)
                % destinationCards.length;
            renderDestinations();
        }

        function stopCarousel() {
            if (carouselTimer) {
                clearInterval(carouselTimer);
                carouselTimer = null;
            }
        }

        function startCarousel() {
            stopCarousel();

            // Keep the destination carousel rotating automatically.

            carouselTimer = setInterval(goNext, 3500);
        }

        nextDestination.addEventListener('click', () => {
            goNext();
            startCarousel();
        });

        prevDestination.addEventListener('click', () => {
            goPrevious();
            startCarousel();
        });

        stage.addEventListener('mouseenter', stopCarousel);
        stage.addEventListener('mouseleave', startCarousel);
        stage.addEventListener('focusin', stopCarousel);
        stage.addEventListener('focusout', startCarousel);

        stage.addEventListener('touchstart', event => {
            swipeStartX = event.changedTouches[0].screenX;
            stopCarousel();
        }, { passive: true });

        stage.addEventListener('touchend', event => {
            const swipeEndX = event.changedTouches[0].screenX;
            const difference = swipeStartX - swipeEndX;

            if (Math.abs(difference) > 40) {
                difference > 0 ? goNext() : goPrevious();
            }

            startCarousel();
        }, { passive: true });

        window.addEventListener('resize', renderDestinations);

        renderDestinations();
        startCarousel();


        // ==========================================
        // TRIP FORM: LARAVEL -> FASTAPI
        // ==========================================

        const tripForm = document.getElementById('tripForm');
        const tripTypeInput = document.getElementById('trip_type');
        const budgetInput = document.getElementById('budget');
        const budgetLabel = document.getElementById('budgetLabel');
        const travelersInput = document.getElementById('travelers');
        const contributionInput = document.getElementById('contribution_per_person');
        const groupSizeField = document.getElementById('groupSizeField');
        const contributionField = document.getElementById('contributionField');
        const submitButton = document.getElementById('submitBtn');
        const formMessage = document.getElementById('formMessage');
        const tripFeedback = document.getElementById('tripFeedback');
        const changeOptionsButton = document.getElementById('changeOptionsBtn');
        const withinBudgetGrid = document.getElementById('withinBudgetGrid');
        const stretchGrid = document.getElementById('stretchGrid');
        const withinBudgetSection = document.getElementById('withinBudgetSection');
        const stretchSection = document.getElementById('stretchSection');
        const tripResultTitle = document.getElementById('tripResultTitle');
        const tripResultActions = document.getElementById('tripResultActions');
        const destinationChoicePanel = document.getElementById('destinationChoicePanel');
        const destinationChoiceQuestion = document.getElementById('destinationChoiceQuestion');
        const firstVisitButton = document.getElementById('firstVisitButton');
        const repeatVisitButton = document.getElementById('repeatVisitButton');
        const visitedPlacesPanel = document.getElementById('visitedPlacesPanel');
        const visitedPlacesInput = document.getElementById('visitedPlacesInput');
        const buildVisitedPlanButton = document.getElementById('buildVisitedPlanButton');
        const tripChatSection = document.getElementById('tripChatSection');
        const chatLog = document.getElementById('chatMessages');
        const chatMessageInput = document.getElementById('chatMessageInput');
        const sendChatMessageButton = document.getElementById('sendChatMessageButton');
        let selectedDestination = '';
        let currentPlanPayload = null;
        let currentPlanResult = null;
        let tripRouteMap = null;
        let tripRouteLayers = null;
        const clientChatHistory = [];
        let chatHistoryGeneration = 0;
        const dateInput = document.getElementById('start_date');
        const tripResult = document.getElementById('tripResult');
        const tripSummary = document.getElementById('tripSummary');
        const tripSceneMessage = document.getElementById('tripSceneMessage');
        const tripSceneLoading = document.getElementById('tripSceneLoading');
        const closeTripSceneButton = document.getElementById('closeTripScene');
        const chatIntro = document.getElementById('chatIntro');
        const tripMainDetails = document.getElementById('tripMainDetails');
        const routeSection = document.getElementById('routeSection');
        const routeHeading = document.getElementById('routeHeading');
        const routeBestVehicle = document.getElementById('routeBestVehicle');
        const routeRecommendation = document.getElementById('routeRecommendation');
        const routeLegs = document.getElementById('routeLegs');
        const routeModes = document.getElementById('routeModes');
        const routeEstimate = document.getElementById('routeEstimate');
        const routeCostSegments = document.getElementById('routeCostSegments');
        const routeMapElement = document.getElementById('routeMap');
        const routeMapStatus = document.getElementById('routeMapStatus');
        const routeNote = document.getElementById('routeNote');
        const routeMapLink = document.getElementById('routeMapLink');
        const tripItinerary = document.getElementById('tripItinerary');
        const recommendationGrid = document.getElementById('recommendationGrid');
        const dailyPlanSection = document.getElementById('dailyPlanSection');
        const dailyPlanGrid = document.getElementById('dailyPlanGrid');
        const hotelSection = document.getElementById('hotelSection');
        const hotelBudgetNote = document.getElementById('hotelBudgetNote');
        const hotelOptions = document.getElementById('hotelOptions');
        const tripNote = document.getElementById('tripNote');

        function renderRouteMap(route) {
            const roadRoute = route && route.road_route;
            const origin = roadRoute && roadRoute.origin;
            const destination = roadRoute && roadRoute.destination;
            if (!origin || !destination) {
                routeMapElement.hidden = true;
                routeMapStatus.textContent = roadRoute && roadRoute.note ? roadRoute.note : '';
                return;
            }
            if (!window.L) {
                routeMapElement.hidden = true;
                routeMapStatus.textContent = 'The interactive map could not be loaded. Open the route link to view OpenStreetMap.';
                return;
            }

            routeMapElement.hidden = false;
            if (!tripRouteMap) {
                tripRouteMap = L.map(routeMapElement);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>'
                }).addTo(tripRouteMap);
                tripRouteLayers = L.featureGroup().addTo(tripRouteMap);
            }
            tripRouteLayers.clearLayers();
            const startPoint = [Number(origin.lat), Number(origin.lon)];
            const endPoint = [Number(destination.lat), Number(destination.lon)];
            L.marker(startPoint).bindPopup(document.createTextNode(`Start: ${origin.label}`)).addTo(tripRouteLayers);
            L.marker(endPoint).bindPopup(document.createTextNode(`Destination: ${destination.label}`)).addTo(tripRouteLayers);

            const geometry = roadRoute.geometry;
            if (geometry && geometry.type === 'LineString' && Array.isArray(geometry.coordinates)) {
                L.geoJSON(geometry, { style: { color: '#28785b', weight: 5, opacity: 0.85 } }).addTo(tripRouteLayers);
            }
            (Array.isArray(route.transport_segments) ? route.transport_segments : []).forEach(segment => {
                if (segment.geometry && segment.geometry.type === 'LineString') {
                    L.geoJSON(segment.geometry, {
                        style: { color: segment.route_type === 'local' ? '#ba8b27' : '#28785b', weight: 4, opacity: 0.75 }
                    }).addTo(tripRouteLayers);
                }
                (Array.isArray(segment.route_waypoints) ? segment.route_waypoints : []).forEach(point => {
                    if (Number.isFinite(Number(point.lat)) && Number.isFinite(Number(point.lon))) {
                        L.marker([Number(point.lat), Number(point.lon)])
                            .bindPopup(document.createTextNode(point.label || 'Itinerary stop'))
                            .addTo(tripRouteLayers);
                    }
                });
            });
            tripRouteMap.fitBounds(tripRouteLayers.getBounds(), { padding: [24, 24] });
            window.setTimeout(() => tripRouteMap.invalidateSize(), 0);

            if (roadRoute.status === 'ready') {
                const routeProvider = roadRoute.provider && roadRoute.provider.includes('OSRM')
                    ? 'OpenStreetMap driving route'
                    : 'OpenRouteService driving route';
                routeMapStatus.textContent = `${routeProvider}: ${Number(roadRoute.distance_km).toLocaleString()} km, about ${Number(roadRoute.duration_minutes).toLocaleString()} minutes (not live traffic).`;
            } else {
                routeMapStatus.textContent = roadRoute.note || 'Showing OpenStreetMap locations; a calculated driving route is unavailable.';
            }
        }
        const copyItineraryButton = document.getElementById('copyItineraryBtn');
        const printItineraryButton = document.getElementById('printItineraryBtn');
        let plannerScrollPosition = 0;

        function getLocalDateString(date = new Date()) {
            return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
        }
        dateInput.min = getLocalDateString();

        function displayFormMessage(message, type) {
            if (!tripResult.hidden) {
                tripSceneMessage.className = `trip-scene-message visible ${type}`;
                tripSceneMessage.textContent = message;
                return;
            }
            formMessage.className = `form-message visible ${type}`;
            formMessage.textContent = message;
        }

        function openTripScene(newSearch = false) {
            if (tripResult.hidden) plannerScrollPosition = window.scrollY;
            if (newSearch) {
                chatHistoryGeneration++;
                currentPlanResult = null;
                tripResultTitle.textContent = 'Finding trip options';
                tripSummary.textContent = '';
                tripSceneMessage.className = 'trip-scene-message';
                tripSceneMessage.textContent = '';
                tripSceneLoading.hidden = false;
                tripChatSection.hidden = false;
                chatIntro.textContent = 'Your destination ideas are loading. Once they appear, choose a place to get a detailed plan.';
                chatMessageInput.placeholder = 'Ask about your trip or a destination idea';
                selectedDestination = '';
                currentPlanPayload = null;
                chatLog.replaceChildren();
                clientChatHistory.length = 0;
                dailyPlanSection.hidden = true;
                routeSection.hidden = true;
                hotelSection.hidden = true;
                tripItinerary.hidden = true;
                tripNote.hidden = true;
                tripResultActions.hidden = true;
                withinBudgetSection.hidden = true;
                stretchSection.hidden = true;
                destinationChoicePanel.hidden = true;
            }
            tripResult.hidden = false;
            document.body.classList.add('trip-scene-open');
        }

        function closeTripScene() {
            tripResult.hidden = true;
            document.body.classList.remove('trip-scene-open');
            window.scrollTo({ top: plannerScrollPosition, behavior: 'auto' });
            submitButton.focus({ preventScroll: true });
        }

        closeTripSceneButton.addEventListener('click', closeTripScene);

        function updateTourTypeFields() {
            const isGroup = tripTypeInput.value === 'group';
            groupSizeField.hidden = !isGroup;
            contributionField.hidden = !isGroup;
            travelersInput.disabled = !isGroup;
            travelersInput.required = isGroup;
            contributionInput.disabled = !isGroup;
            contributionInput.required = isGroup;
            budgetInput.readOnly = isGroup;
            budgetInput.required = !isGroup;
            budgetLabel.textContent = isGroup ? '◈  Total Group Budget (calculated)' : '◈  Your Budget';
            if (isGroup) updateGroupBudget();
        }

        function updateGroupBudget() {
            const members = Number(travelersInput.value);
            const contribution = Number(contributionInput.value);
            budgetInput.value = Number.isInteger(members) && members >= 2 && contribution > 0
                ? String(members * contribution)
                : '';
        }

        tripTypeInput.addEventListener('change', updateTourTypeFields);
        travelersInput.addEventListener('input', updateGroupBudget);
        contributionInput.addEventListener('input', updateGroupBudget);
        updateTourTypeFields();
        function clearFormMessage() {
            formMessage.className = 'form-message';
            formMessage.textContent = '';
        }
        function getReadableError(result, status) {
            if (result && result.errors && typeof result.errors === 'object') {
                const messages = Object.values(result.errors).flat().filter(Boolean);
                if (messages.length) return messages.join(' ');
            }
            if (result && typeof result.detail === 'string') return result.detail;
            if (result && typeof result.message === 'string') return result.message;
            if (status === 419) return 'Your session has expired. Refresh this page and try again.';
            if (status === 422) return 'Some trip details are invalid. Please check the form and try again.';
            if (status >= 500) return 'The trip-planning service encountered a server error. Please check both servers and try again.';
            return 'The request could not be processed. Please try again.';
        }

        async function requestTripPlan(payload, button, loadingText, endpoint = 'trip.plan') {
            const isNewSearch = button === submitButton;
            if (isNewSearch) openTripScene(true);
            else {
                chatHistoryGeneration++;
                clientChatHistory.length = 0;
                chatLog.replaceChildren();
            }
            tripSceneLoading.hidden = false;
            tripSceneMessage.className = 'trip-scene-message';
            tripSceneMessage.textContent = '';
            const oldText = button.textContent;
            button.disabled = true;
            button.textContent = loadingText;
            try {
                const endpointUrl = endpoint === 'trip.recommendations'
                    ? @json(route('trip.recommendations')) : @json(route('trip.plan'));
                const response = await fetch(endpointUrl, {
                    method: 'POST', credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json', 'Accept': 'application/json',
                        'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: JSON.stringify(payload)
                });
                let result;
                try { result = await response.json(); }
                catch (_) { throw new Error(`The server returned an unreadable response (HTTP ${response.status}).`); }
                if (!response.ok) throw new Error(getReadableError(result, response.status));
                showTripResult(result, payload);
                displayFormMessage(
                    result.budget_warning || (result.itinerary ? 'Your selected destination itinerary is ready.' : 'Here are your updated trip options.'),
                    result.budget_warning ? 'warning' : 'success'
                );
            } catch (error) {
                tripSceneLoading.hidden = true;
                displayFormMessage(error instanceof TypeError
                    ? 'Could not connect to the trip-planning service. Check that both servers are running.'
                    : (error.message || 'Something went wrong. Please try again.'), 'error');
            } finally {
                button.disabled = false;
                button.textContent = oldText;
            }
        }

        function showTripResult(result, payload, {
            preserveStretch = false,
            preservePlan = false
        } = {}) {
            const incoming = result && result.data && typeof result.data === 'object' ? result.data : result;
            const body = preservePlan && currentPlanResult
                ? {
                    ...currentPlanResult,
                    ...incoming,
                    itinerary: incoming.itinerary || currentPlanResult.itinerary || '',
                    route_guidance: incoming.route_guidance || currentPlanResult.route_guidance,
                    daily_plan: Array.isArray(incoming.daily_plan) ? incoming.daily_plan : currentPlanResult.daily_plan,
                    hotel_options: Array.isArray(incoming.hotel_options) ? incoming.hotel_options : currentPlanResult.hotel_options
                }
                : incoming;
            currentPlanResult = body;
            currentPlanPayload = { ...(body.trip || payload) };
            const itinerary = typeof body.itinerary === 'string' ? body.itinerary.trim() : '';
            tripResultTitle.textContent = itinerary ? 'Your selected destination plan' : 'Choose a destination to plan';

            const trip = body.trip && typeof body.trip === 'object' ? body.trip : {};
            const destination = trip.destination || body.destination || (body.details && body.details.destination) || '';
            const duration = trip.duration_days || payload.duration_days;
            const departure = trip.departure_city || payload.departure_city;
            const currency = trip.currency || payload.currency;
            const budget = trip.budget ?? payload.budget;
            const summary = [];
            if (destination) summary.push(`Destination: ${destination}`);
            summary.push(`${duration}-day trip`);
            if (departure) summary.push(`Starting from ${departure}`);
            if (budget !== undefined && budget !== null && budget !== '') {
                summary.push(`Budget: ${currency} ${Number(budget).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
            }
            if (trip.trip_type === 'group') {
                summary.push(`${trip.travelers} members · ${currency} ${Number(trip.contribution_per_person).toLocaleString(undefined, { maximumFractionDigits: 2 })} each`);
            }
            tripSummary.textContent = summary.join(' · ');
            chatIntro.textContent = destination
                ? `Ask TripMate about ${destination}: transport, food, stays, routes, or things to do.`
                : 'Choose a destination to start a conversation about your trip. Guests get five free assistant messages.';

            const route = body.route_guidance;
            routeSection.hidden = !itinerary || !route;
            if (route) {
                routeHeading.textContent = `Route: ${route.origin} to ${route.destination}`;
                routeBestVehicle.textContent = route.best_vehicle
                    ? `Suggested vehicle combination: ${route.best_vehicle}`
                    : '';
                routeRecommendation.textContent = route.recommended || '';
                routeLegs.replaceChildren();
                (Array.isArray(route.legs) ? route.legs : []).forEach(leg => {
                    const item = document.createElement('li');
                    const routeLine = document.createElement('strong');
                    routeLine.textContent = `${leg.from} → ${leg.to}`;
                    item.appendChild(routeLine);
                    item.appendChild(document.createElement('br'));
                    item.appendChild(document.createTextNode(`${leg.vehicle}. ${leg.note || ''}`));
                    routeLegs.appendChild(item);
                });
                routeLegs.hidden = routeLegs.childElementCount === 0;
                routeModes.replaceChildren();
                (Array.isArray(route.modes) ? route.modes : []).forEach(mode => {
                    const item = document.createElement('li');
                    item.textContent = `${mode.name}: ${mode.guidance}`;
                    routeModes.appendChild(item);
                });
                const totalTransport = route.total_transport_estimate || {};
                routeEstimate.textContent = totalTransport.status !== 'unavailable'
                    && totalTransport.minimum !== null && totalTransport.minimum !== undefined
                    ? `${totalTransport.status === 'partial' ? 'Partial estimated transportation total' : 'Estimated transportation total'}: ${totalTransport.currency} ${Number(totalTransport.minimum).toLocaleString()}–${Number(totalTransport.maximum).toLocaleString()} for the full tour. ${totalTransport.note || ''}`
                    : `Transportation cost range unavailable. ${totalTransport.note || ''}`;
                routeCostSegments.replaceChildren();
                (Array.isArray(route.transport_segments) ? route.transport_segments : []).forEach(segment => {
                    const item = document.createElement('li');
                    const fare = segment.fare || {};
                    const distance = segment.distance_km === null || segment.distance_km === undefined
                        ? 'distance unavailable'
                        : `${Number(segment.distance_km).toLocaleString()} km · about ${Number(segment.duration_minutes).toLocaleString()} min`;
                    const cost = fare.status === 'estimated_range'
                        ? `${fare.currency} ${Number(fare.minimum).toLocaleString()}–${Number(fare.maximum).toLocaleString()}`
                        : 'fare range unavailable';
                    item.textContent = `${segment.from} → ${segment.to}: ${distance}; ${segment.vehicle}; estimated ${segment.fare && segment.fare.return_trip ? 'return fare ' : ''}${cost}.`;
                    routeCostSegments.appendChild(item);
                });
                renderRouteMap(route);
                routeNote.textContent = route.note || '';
                routeMapLink.href = route.route_url || '#';
                routeMapLink.textContent = route.route_label || 'Open route directions';
                routeMapLink.hidden = !route.route_url;
            }

            const recommendations = body.recommendations || {};
            const recommendationGroups = Array.isArray(recommendations)
                ? {
                    within_budget: recommendations.filter(option => option.within_budget),
                    stretch: recommendations.filter(option => !option.within_budget)
                }
                : recommendations;
            withinBudgetGrid.replaceChildren();
            if (!preserveStretch) stretchGrid.replaceChildren();
            const withinOptions = Array.isArray(recommendationGroups.within_budget) ? recommendationGroups.within_budget : [];
            const stretchOptions = Array.isArray(recommendationGroups.stretch) ? recommendationGroups.stretch : [];
            withinBudgetSection.hidden = withinOptions.length === 0;
            if (!preserveStretch) stretchSection.hidden = stretchOptions.length === 0;
            destinationChoicePanel.hidden = true;
            Object.entries({ within_budget: withinOptions, stretch: stretchOptions }).forEach(([groupName, options]) => {
                if (preserveStretch && groupName === 'stretch') return;
                options.forEach(option => {
                    const card = document.createElement('article');
                    card.className = 'recommendation-card';
                    if (typeof option.image_url === 'string' && option.image_url.startsWith('https://')) {
                        const image = document.createElement('img');
                        image.src = option.image_url;
                        image.alt = `Scenery in ${option.name}`;
                        image.loading = 'lazy';
                        card.appendChild(image);
                    }
                    const content = document.createElement('div');
                    content.className = 'recommendation-content';
                    const title = document.createElement('h3');
                    title.textContent = `${option.name || 'Destination'}${option.country ? `, ${option.country}` : ''}`;
                    content.appendChild(title);
                    const description = document.createElement('p');
                    description.textContent = option.summary || option.reason || '';
                    content.appendChild(description);
                    const cost = document.createElement('p');
                    cost.className = 'recommendation-cost';
                    const formattedCost = Number(option.estimated_total).toLocaleString(undefined, { maximumFractionDigits: 0 });
                    cost.textContent = `Estimated total: ${option.currency || currency} ${formattedCost}${option.within_budget ? ' · within budget' : ' · over budget'}`;
                    content.appendChild(cost);
                    if (option.source && typeof option.source.url === 'string' && option.source.url.startsWith('https://')) {
                        const source = document.createElement('a');
                        source.className = 'recommendation-source';
                        source.href = option.source.url;
                        source.target = '_blank';
                        source.rel = 'noopener noreferrer';
                        source.textContent = `Research: ${option.source.name || 'source'}`;
                        content.appendChild(source);
                    }
                    const actions = document.createElement('div');
                    actions.className = 'recommendation-actions';
                    const choose = document.createElement('button');
                    choose.type = 'button';
                    choose.textContent = 'Choose this destination';
                    choose.addEventListener('click', () => {
                        selectedDestination = option.name;
                        currentPlanPayload = { ...currentPlanPayload, destination: option.name };
                        chatMessageInput.placeholder = `Ask about ${option.name}: routes, food, hotels...`;
                        tripChatSection.hidden = false;
                        chatIntro.textContent = `Ask TripMate about ${option.name}: transport, food, stays, routes, or things to do.`;
                        const knownVisited = Array.isArray(currentPlanPayload.visited_places) ? currentPlanPayload.visited_places : [];
                        destinationChoiceQuestion.textContent = knownVisited.length
                            ? `I’ll avoid the places you listed for ${selectedDestination}. Add or remove places below.`
                            : `Is this your first visit to ${selectedDestination}?`;
                        visitedPlacesInput.value = knownVisited.join(', ');
                        firstVisitButton.hidden = knownVisited.length > 0;
                        repeatVisitButton.hidden = knownVisited.length > 0;
                        visitedPlacesPanel.hidden = knownVisited.length === 0;
                        destinationChoicePanel.hidden = false;
                        destinationChoicePanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    });
                    actions.appendChild(choose);
                    const ask = document.createElement('button');
                    ask.type = 'button';
                    ask.textContent = 'Ask about this place';
                    ask.addEventListener('click', () => {
                        currentPlanPayload = { ...currentPlanPayload, destination: option.name };
                        chatMessageInput.placeholder = `Ask about ${option.name}: safety, food, weather, hotels...`;
                        tripChatSection.hidden = false;
                        chatIntro.textContent = `Ask TripMate about ${option.name}: safety, food, weather, hotels, or routes.`;
                        chatMessageInput.focus();
                        tripMainDetails.scrollTo({ top: 0, behavior: 'smooth' });
                    });
                    actions.appendChild(ask);
                    content.appendChild(actions);
                    card.appendChild(content);
                    (groupName === 'stretch' ? stretchGrid : withinBudgetGrid).appendChild(card);
                });
            });

            dailyPlanGrid.replaceChildren();
            const dailyPlan = Array.isArray(body.daily_plan) ? body.daily_plan : [];
            dailyPlanSection.hidden = !itinerary || dailyPlan.length === 0;
            dailyPlan.forEach(day => {
                const dayCard = document.createElement('article');
                dayCard.className = 'daily-plan-card';
                const heading = document.createElement('h3');
                heading.textContent = `Day ${day.day}: ${day.area}`;
                dayCard.appendChild(heading);
                if (day.transport && typeof day.transport === 'object') {
                    const transport = document.createElement('div');
                    transport.className = 'day-transport';
                    const transportTitle = document.createElement('strong');
                    transportTitle.textContent = `How to get around today: ${day.transport.vehicle || 'Local transport'}`;
                    transport.appendChild(transportTitle);
                    if (day.transport.guidance) {
                        transport.appendChild(document.createTextNode(day.transport.guidance));
                    }
                    const unmappedStops = day.road_route && Array.isArray(day.road_route.unmapped_waypoints)
                        ? day.road_route.unmapped_waypoints : [];
                    if (unmappedStops.length) {
                        const mapNote = document.createElement('span');
                        mapNote.textContent = `\nNot mapped because the location could not be verified: ${unmappedStops.join(', ')}.`;
                        transport.appendChild(mapNote);
                    }
                    (Array.isArray(day.transport_segments) ? day.transport_segments : []).forEach(segment => {
                        const fare = segment.fare || {};
                        const cost = fare.status === 'estimated_range'
                            ? `${fare.currency} ${Number(fare.minimum).toLocaleString()}–${Number(fare.maximum).toLocaleString()}`
                            : 'fare range unavailable';
                        const segmentLine = document.createElement('span');
                        segmentLine.textContent = `\n${segment.from} → ${segment.to}: ${segment.distance_km === null ? 'distance unavailable' : `${segment.distance_km} km, about ${segment.duration_minutes} min`}; ${segment.fare_vehicle}: ${cost}.`;
                        transport.appendChild(segmentLine);
                    });
                    dayCard.appendChild(transport);
                }
                const attractions = document.createElement('div');
                attractions.className = 'attraction-list';
                (Array.isArray(day.stops) ? day.stops : []).forEach(stop => {
                    const place = document.createElement('article');
                    place.className = 'attraction-card';
                    if (typeof stop.image_url === 'string' && stop.image_url.startsWith('https://')) {
                        const image = document.createElement('img');
                        image.src = stop.image_url;
                        image.alt = `Photo of ${stop.name}`;
                        image.loading = 'lazy';
                        place.appendChild(image);
                    }
                    const details = document.createElement('div');
                    const name = document.createElement('h4');
                    name.textContent = stop.name || 'Suggested stop';
                    details.appendChild(name);
                    const description = document.createElement('p');
                    description.textContent = stop.summary || '';
                    details.appendChild(description);
                    if (stop.source && typeof stop.source.url === 'string' && stop.source.url.startsWith('https://')) {
                        const source = document.createElement('a');
                        source.href = stop.source.url;
                        source.target = '_blank';
                        source.rel = 'noopener noreferrer';
                        source.textContent = `Photo and details: ${stop.source.name || 'source'}`;
                        details.appendChild(source);
                    }
                    place.appendChild(details);
                    attractions.appendChild(place);
                });
                dayCard.appendChild(attractions);
                dailyPlanGrid.appendChild(dayCard);
            });

            hotelOptions.replaceChildren();
            const stays = Array.isArray(body.hotel_options) ? body.hotel_options : [];
            hotelSection.hidden = !itinerary || stays.length === 0;
            if (stays.length) {
                const firstStay = stays[0];
                hotelBudgetNote.textContent = `Planning target: up to ${firstStay.currency} ${Number(firstStay.nightly_budget).toLocaleString()} per night, based on 35% of your total budget. Search listings and confirm the actual rate before booking.`;
                stays.forEach((stay, index) => {
                    const card = document.createElement('article');
                    card.className = 'hotel-choice';
                    const heading = document.createElement('h4');
                    heading.textContent = `${stay.area} stay search`;
                    card.appendChild(heading);
                    const nightly = document.createElement('p');
                    nightly.textContent = `Target: up to ${stay.currency} ${Number(stay.nightly_budget).toLocaleString()} per night`;
                    card.appendChild(nightly);
                    const caution = document.createElement('p');
                    caution.textContent = stay.note || '';
                    card.appendChild(caution);
                    if (typeof stay.search_url === 'string' && stay.search_url.startsWith('https://www.google.com/maps/')) {
                        const link = document.createElement('a');
                        link.href = stay.search_url;
                        link.target = '_blank';
                        link.rel = 'noopener noreferrer';
                        link.textContent = 'Compare hotels on Google Maps';
                        card.appendChild(link);
                    }
                    hotelOptions.appendChild(card);
                });
            }

            // AI output is inserted as plain text, never interpreted as HTML.
            tripItinerary.textContent = itinerary;
            tripItinerary.style.whiteSpace = 'pre-wrap';
            tripItinerary.hidden = !itinerary;
            tripResultActions.hidden = !itinerary;
            const note = typeof body.note === 'string' ? body.note.trim() : '';
            tripNote.textContent = note;
            tripNote.hidden = !note;
            tripChatSection.hidden = false;
            tripSceneLoading.hidden = true;
            if (typeof body.reply === 'string' && body.reply.trim()) {
                appendChatMessage(body.reply, 'assistant', '', body.answer_media || [], body.answer_sources || []);
            }
            tripResult.hidden = false;
            document.body.classList.add('trip-scene-open');
            if (itinerary) {
                window.requestAnimationFrame(() => dailyPlanSection.scrollIntoView({ behavior: 'smooth', block: 'start' }));
            }
        }

        function appendChatMessage(message, role, signupUrl = '', media = [], sources = []) {
            const bubble = document.createElement('div');
            bubble.className = `chat-message ${role}`;
            bubble.textContent = message;
            if (signupUrl.startsWith('/') && role === 'assistant') {
                bubble.appendChild(document.createTextNode(' '));
                const link = document.createElement('a');
                link.href = signupUrl;
                link.textContent = 'Create a free account';
                bubble.appendChild(link);
            }
            (Array.isArray(media) ? media : []).forEach(item => {
                if (typeof item.image_url !== 'string' || !item.image_url.startsWith('https://')) return;
                const image = document.createElement('img');
                image.src = item.image_url;
                image.alt = item.alt || 'Destination photo';
                image.loading = 'lazy';
                image.style.cssText = 'display:block;width:min(100%,420px);max-height:240px;object-fit:cover;border-radius:10px;margin-top:10px';
                bubble.appendChild(image);
            });
            (Array.isArray(sources) ? sources : []).forEach(item => {
                bubble.appendChild(document.createElement('br'));
                const hasSecureUrl = typeof item.url === 'string' && item.url.startsWith('https://');
                const source = document.createElement(hasSecureUrl ? 'a' : 'span');
                if (hasSecureUrl) {
                    source.href = item.url;
                    source.target = '_blank';
                    source.rel = 'noopener noreferrer';
                }
                source.textContent = hasSecureUrl
                    ? `${item.name || 'Source'}${item.retrieved_at ? ` · Retrieved ${item.retrieved_at}` : ''}`
                    : `Local knowledge: ${item.name || 'TripMate source'}${item.source ? ` (${item.source})` : ''}`;
                bubble.appendChild(source);
            });
            chatLog.appendChild(bubble);
            clientChatHistory.push({ role, content: message.slice(0, 1800) });
            chatLog.scrollTop = chatLog.scrollHeight;
        }

        async function sendChatMessage(suggestedMessage = '') {
            const message = suggestedMessage || chatMessageInput.value.trim();
            if (!message || !currentPlanPayload) return;
            chatHistoryGeneration++;
            const history = clientChatHistory.slice(-10);
            appendChatMessage(message, 'user');
            chatMessageInput.value = '';
            sendChatMessageButton.disabled = true;
            sendChatMessageButton.textContent = 'Thinking...';
            try {
                const planDetails = currentPlanResult && currentPlanResult.details;
                const planEstimate = planDetails
                    && planDetails.budget_breakdown
                    && currentPlanPayload.destination === planDetails.destination
                    && String(currentPlanPayload.currency).toUpperCase() === String(planDetails.currency).toUpperCase()
                    ? {
                        destination: planDetails.destination,
                        budget: currentPlanPayload.budget,
                        currency: planDetails.currency,
                        estimated_total: planDetails.estimated_total,
                        budget_difference: planDetails.budget_difference,
                        within_budget: planDetails.within_budget,
                        breakdown: planDetails.budget_breakdown
                    }
                    : null;
                const response = await fetch(@json(route('trip.chat')), {
                    method: 'POST', credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json', 'Accept': 'application/json',
                        'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: JSON.stringify({ message, trip: currentPlanPayload, history, plan_estimate: planEstimate })
                });
                const result = await response.json();
                if (result.needs_signup) {
                    appendChatMessage(result.message, 'assistant', result.signup_url || '/register');
                    return;
                }
                if (!response.ok) throw new Error(getReadableError(result, response.status));
                showTripResult(result, currentPlanPayload, { preserveStretch: true, preservePlan: true });
                displayFormMessage(result.budget_warning || 'TripMate updated the recommendations from your message.', result.budget_warning ? 'warning' : 'success');
            } catch (error) {
                appendChatMessage(error.message || 'I could not reach the TripMate service. Try again.', 'assistant');
            } finally {
                sendChatMessageButton.disabled = false;
                sendChatMessageButton.textContent = 'Send';
            }
        }

        sendChatMessageButton.addEventListener('click', () => sendChatMessage());
        document.querySelectorAll('[data-trip-question]').forEach(button => {
            button.addEventListener('click', () => sendChatMessage(button.dataset.tripQuestion));
        });
        chatMessageInput.addEventListener('keydown', event => {
            if (event.key === 'Enter') sendChatMessage();
        });
        const historyGeneration = chatHistoryGeneration;
        fetch(@json(route('trip.chat.history')), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(response => response.ok ? response.json() : null)
            .then(data => {
                if (historyGeneration !== chatHistoryGeneration) return;
                (data && Array.isArray(data.messages) ? data.messages : []).forEach(item => {
                const context = item.context && typeof item.context === 'object' ? item.context : {};
                appendChatMessage(item.content, item.role === 'user' ? 'user' : 'assistant', '', context.answer_media || [], context.answer_sources || []);
                });
            })
            .catch(() => {});

        changeOptionsButton.addEventListener('click', () => {
            if (!currentPlanPayload) return;
            const feedback = tripFeedback.value.trim();
            const alreadyExcluded = currentPlanPayload.excluded_destinations || [];
            const shown = Array.from(recommendationGrid.querySelectorAll('.recommendation-card h3'))
                .map(heading => heading.textContent.split(',')[0].trim());
            const nextPayload = {
                ...currentPlanPayload,
                destination: null,
                feedback,
                excluded_destinations: [...new Set([...alreadyExcluded, ...shown])]
            };
            requestTripPlan(nextPayload, changeOptionsButton, 'Finding other options...', 'trip.recommendations');
        });

        firstVisitButton.addEventListener('click', () => {
            const nextPayload = { ...currentPlanPayload, destination: selectedDestination, first_visit: true, visited_places: [] };
            requestTripPlan(nextPayload, firstVisitButton, 'Building itinerary...');
        });

        repeatVisitButton.addEventListener('click', () => {
            visitedPlacesPanel.hidden = false;
            visitedPlacesInput.focus();
        });

        buildVisitedPlanButton.addEventListener('click', () => {
            const visitedPlaces = visitedPlacesInput.value.split(',').map(place => place.trim()).filter(Boolean);
            if (!visitedPlaces.length) {
                displayFormMessage('Add at least one place you have already visited so TripMate can suggest a different route.', 'error');
                visitedPlacesInput.focus();
                return;
            }
            const nextPayload = { ...currentPlanPayload, destination: selectedDestination, first_visit: false, visited_places: visitedPlaces };
            requestTripPlan(nextPayload, buildVisitedPlanButton, 'Finding new places...');
        });

        tripForm.addEventListener('submit', async event => {
            event.preventDefault();
            clearFormMessage();
            if (!tripForm.reportValidity()) return;

            const formData = new FormData(tripForm);
            const budget = Number(formData.get('budget'));
            const durationDays = Number(formData.get('duration_days'));
            const tripType = String(formData.get('trip_type') || 'single');
            const travelers = tripType === 'group' ? Number(formData.get('travelers')) : 1;
            const contribution = tripType === 'group' ? Number(formData.get('contribution_per_person')) : budget;
            const departureCity = String(formData.get('departure_city') || '').trim();
            const startDate = String(formData.get('start_date') || '');

            if (!Number.isFinite(budget) || budget <= 0) {
                displayFormMessage('Please enter a budget greater than zero.', 'error'); return;
            }
            if (tripType === 'group' && (!Number.isInteger(travelers) || travelers < 2 || travelers > 100 || !Number.isFinite(contribution) || contribution <= 0)) {
                displayFormMessage('For a group tour, enter 2–100 members and a contribution greater than zero for each member.', 'error'); return;
            }
            if (!Number.isInteger(durationDays) || durationDays < 1) {
                displayFormMessage('Please select a valid trip duration.', 'error'); return;
            }
            if (startDate < getLocalDateString()) {
                displayFormMessage('The departure date cannot be in the past.', 'error'); return;
            }

            const payload = {
                budget,
                currency: String(formData.get('currency') || 'BDT'),
                duration_days: durationDays,
                departure_city: departureCity,
                start_date: startDate,
                travel_scope: String(formData.get('travel_scope') || 'anywhere'),
                interests: formData.getAll('interests[]'),
                trip_type: tripType,
                travelers,
                contribution_per_person: contribution
            };

            requestTripPlan(payload, submitButton, 'Finding destinations...', 'trip.recommendations');
            return;

            submitButton.disabled = true;
            submitButton.textContent = 'Creating your itinerary...';
            try {
                const response = await fetch(@json(route('trip.plan')), {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: JSON.stringify(payload)
                });

                let result;
                try {
                    result = await response.json();
                } catch (_) {
                    throw new Error(response.ok
                        ? 'The server returned an unreadable response. Please check the Laravel controller.'
                        : `The request failed (HTTP ${response.status}). Please try again.`);
                }
                if (!response.ok) throw new Error(getReadableError(result, response.status));
                showTripResult(result, payload);
                displayFormMessage('Your personalized itinerary is ready below.', 'success');
            } catch (error) {
                displayFormMessage(error instanceof TypeError
                    ? 'Could not connect to the trip-planning service. Make sure Laravel and the Python FastAPI server are both running.'
                    : (error.message || 'Something went wrong. Please try again.'), 'error');
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = 'Plan My Adventure →';
            }
        });

        copyItineraryButton.addEventListener('click', async () => {
            const summary = tripSummary.textContent.trim();
            const itinerary = tripItinerary.textContent.trim();
            const note = tripNote.hidden ? '' : tripNote.textContent.trim();
            const textToCopy = ['TripMate AI — Your Trip Itinerary', summary, '', itinerary, note ? `\nNote: ${note}` : ''].filter(Boolean).join('\n');
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(textToCopy);
                } else {
                    const area = document.createElement('textarea');
                    area.value = textToCopy;
                    area.setAttribute('readonly', '');
                    area.style.position = 'fixed';
                    area.style.opacity = '0';
                    document.body.appendChild(area);
                    area.select();
                    const copied = document.execCommand('copy');
                    area.remove();
                    if (!copied) throw new Error('Copy failed');
                }
                const oldLabel = copyItineraryButton.textContent;
                copyItineraryButton.textContent = 'Copied!';
                window.setTimeout(() => { copyItineraryButton.textContent = oldLabel; }, 1800);
            } catch (_) {
                displayFormMessage('Unable to copy automatically. Select the itinerary text and copy it manually.', 'error');
            }
        });

        printItineraryButton.addEventListener('click', () => {
            if (!tripResult.hidden) window.print();
        });

        const resumeTrip = @json($resumeTrip ?? null);
        if (resumeTrip && typeof resumeTrip === 'object') {
            openTripScene(true);
            requestTripPlan(resumeTrip, submitButton, 'Resuming your trip...', 'trip.recommendations');
        }
    </script>
</body>
</html>
