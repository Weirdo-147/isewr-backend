                # If no specific findings, add generic ones
                if not findings:
                    findings = [
                        "No clear signs of deepfake manipulation detected",
                        "Video appears to be authentic based on analyzed frames"
                    ]
                
                return {
                    "success": True,
                    "message": "Video analysis completed",
                    "video_id": video_id,
                    "confidence": confidence,
                    "face_confidence": face_confidence,
                    "lip_sync_confidence": avg_deepfake_score,
                    "motion_confidence": deepfake_confidence,
                    "findings": findings
                } 